import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class DaylightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.config = self.home/'config/omarchy/jialing-daylight.json'
        self.config.parent.mkdir(parents=True)
        self.config.write_text(json.dumps({'city':'Paris','latitude':48.8566,'longitude':2.3522,'timezone':'Europe/Paris'}))
        current = self.home/'state/omarchy/current/theme.name';current.parent.mkdir(parents=True);current.write_text('jialing')
        self.env = dict(os.environ, XDG_CONFIG_HOME=str(self.home/'config'), XDG_STATE_HOME=str(self.home/'state'))

    def status(self, now):
        result = subprocess.run([sys.executable,str(ROOT/'daylight.py'),'--status','--now',now],env=self.env,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        return json.loads(result.stdout)

    def test_day_and_night_in_winter_and_summer(self):
        for day in ('2026-01-15','2026-07-15'):
            self.assertEqual(self.status(day+'T12:00:00+01:00')['theme'],'jialing-light')
            self.assertEqual(self.status(day+'T00:00:00+01:00')['theme'],'jialing')

    def test_manual_unrelated_theme_is_preserved(self):
        (self.home/'state/omarchy/current/theme.name').write_text('tokyo-night')
        report = self.status('2026-07-15T12:00:00+02:00')
        self.assertFalse(report['should_change'])
        self.assertEqual(report['current_theme'],'tokyo-night')

    def test_sunrise_is_light_and_sunset_is_dark(self):
        report = self.status('2026-09-15T12:00:00+02:00')
        self.assertEqual(self.status(report['sunrise'])['theme'],'jialing-light')
        self.assertEqual(self.status(report['sunset'])['theme'],'jialing')

    def test_invalid_coordinates_fail_without_desktop_changes(self):
        self.config.write_text(json.dumps({'city':'Invalid','latitude':999,'longitude':2,'timezone':'Europe/Paris'}))
        result = subprocess.run([sys.executable,str(ROOT/'daylight.py'),'--status'],env=self.env,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('latitude',result.stderr.lower())

    def test_polar_day_and_night(self):
        self.config.write_text(json.dumps({'city':'Tromso','latitude':69.6492,'longitude':18.9553,'timezone':'Europe/Oslo'}))
        self.assertEqual(self.status('2026-06-21T00:00:00+02:00')['theme'],'jialing-light')
        self.assertEqual(self.status('2026-12-21T12:00:00+01:00')['theme'],'jialing')

    def test_failed_location_lookup_uses_configured_fallback(self):
        import contextlib, importlib.util, io
        from unittest.mock import patch
        spec = importlib.util.spec_from_file_location('daylight', ROOT/'daylight.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        config = json.loads(self.config.read_text());config['auto_location']=True;self.config.write_text(json.dumps(config))
        with patch.dict(os.environ,self.env), patch.object(sys,'argv',['daylight.py','--status','--refresh-location']), patch('urllib.request.urlopen',side_effect=OSError('offline')), contextlib.redirect_stdout(io.StringIO()) as output:
            module.main()
        self.assertEqual(json.loads(output.getvalue())['city'],'Paris')
        self.assertIn('fallback',json.loads(output.getvalue())['location_source'])

    def test_corrupt_cached_location_falls_back_without_network_in_status(self):
        cache = self.home/'state/omarchy/jialing-location.json'
        cache.write_text(json.dumps({'location':[], 'checked_at':0}))
        config = json.loads(self.config.read_text())
        config['auto_location'] = True
        self.config.write_text(json.dumps(config))
        self.assertEqual(self.status('2026-09-15T12:00:00+02:00')['city'], 'Paris')

    def test_scheduler_caches_successful_lookup_for_an_hour_without_storing_ip(self):
        import contextlib, importlib.util, io
        from unittest.mock import patch, MagicMock
        spec = importlib.util.spec_from_file_location('daylight', ROOT/'daylight.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.config.write_text('{"auto_location":true}')
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            'latitude':48.85, 'longitude':2.35, 'timezone':'Europe/Paris',
            'city':'Paris', 'ip':'198.51.100.10'}).encode()
        with patch.dict(os.environ,self.env), patch.object(sys,'argv',['daylight.py']), patch('urllib.request.urlopen',return_value=response) as lookup, patch('subprocess.run') as command, patch('time.time',return_value=1000000), contextlib.redirect_stdout(io.StringIO()):
            module.main()
            module.main()
            self.assertEqual(lookup.call_count, 1)
            with patch('time.time',return_value=1003601):
                module.main()
            self.assertEqual(lookup.call_count, 2)
        cache = (self.home/'state/omarchy/jialing-location.json').read_text()
        self.assertNotIn('198.51.100.10', cache)
        self.assertNotIn('"ip"', cache)

    def test_missing_location_fails_clearly_and_manual_override_skips_lookup(self):
        self.config.unlink()
        result = subprocess.run([sys.executable,str(ROOT/'daylight.py'),'--status'],env=self.env,capture_output=True,text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('latitude', result.stderr)
        (self.home/'state/omarchy/current/theme.name').write_text('tokyo-night')
        result = subprocess.run([sys.executable,str(ROOT/'daylight.py')],env=self.env,capture_output=True,text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.home/'state/omarchy/jialing-location.json').exists())
