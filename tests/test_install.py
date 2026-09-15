import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='jialing test ')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.config = self.home / 'config'
        self.env = dict(os.environ, HOME=str(self.home), XDG_CONFIG_HOME=str(self.config), XDG_DATA_HOME=str(self.home/'data'), XDG_STATE_HOME=str(self.home/'state'))

    def run_cli(self, *args, success=True):
        result = subprocess.run([sys.executable, str(ROOT/'install.py'), '--no-apply', *args], env=self.env, capture_output=True, text=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        return result

    def test_install_both_themes_preserves_existing_wallpaper(self):
        background = self.config/'omarchy/themes/jialing/backgrounds/personal.jpg'
        background.parent.mkdir(parents=True)
        background.write_bytes(b'personal wallpaper')
        report = self.run_cli()
        for theme in ('jialing', 'jialing-light'):
            self.assertTrue((self.config/'omarchy/themes'/theme/'colors.toml').is_file())
        self.assertEqual(background.read_bytes(), b'personal wallpaper')
        self.assertTrue(Path(report['backup']).is_dir())

    def test_restore_returns_previous_theme_and_removes_new_assets(self):
        original = self.config/'omarchy/themes/jialing/colors.toml'
        original.parent.mkdir(parents=True)
        original.write_text('old palette')
        report = self.run_cli()
        self.run_cli('--restore', report['backup'])
        self.assertEqual(original.read_text(), 'old palette')
        self.assertFalse((self.config/'omarchy/themes/jialing-light/colors.toml').exists())

    def test_restore_refuses_to_overwrite_edits_made_after_install(self):
        report = self.run_cli()
        asset = self.config/'omarchy/themes/jialing/colors.toml'
        asset.write_text('my later changes')
        self.run_cli('--restore', report['backup'], success=False)
        self.assertEqual(asset.read_text(), 'my later changes')

    def test_profile_preserves_unrelated_rules_and_shortcuts_and_is_repeatable(self):
        font = self.config/'fontconfig/fonts.conf'
        font.parent.mkdir(parents=True)
        original = '<fontconfig><!-- keep me --><alias><family>serif</family><prefer><family>Noto Serif</family></prefer></alias></fontconfig>'
        font.write_text(original)
        terminal = self.config/'ghostty/config'
        terminal.parent.mkdir(parents=True)
        terminal.write_text('font-size = 15\nkeybind = ctrl+c=copy_to_clipboard\n')
        first = self.run_cli('--profile')
        after = font.read_text()
        self.assertIn('<!-- keep me -->', after)
        self.assertIn('Noto Serif', after)
        self.assertIn('keybind = ctrl+c=copy_to_clipboard', terminal.read_text())
        self.run_cli('--profile')
        self.assertEqual(font.read_text(), after)
        self.run_cli('--restore', first['backup'])
        self.assertEqual(font.read_text(), original)
        self.assertIn('font-size = 15', terminal.read_text())

    def test_symlink_destination_is_rejected_before_any_theme_is_written(self):
        outside = self.home/'outside'; outside.mkdir()
        target = self.config/'omarchy/themes/jialing-light';target.parent.mkdir(parents=True)
        target.symlink_to(outside, target_is_directory=True)
        self.run_cli(success=False)
        self.assertFalse((self.config/'omarchy/themes/jialing/colors.toml').exists())
        self.assertEqual(list(outside.iterdir()), [])

    def test_optional_daylight_install_preserves_location_and_is_restorable(self):
        location = self.config/'omarchy/jialing-daylight.json'
        location.parent.mkdir(parents=True)
        original = '{"latitude": 48.85, "longitude": 2.35, "timezone": "Europe/Paris", "custom": true}'
        location.write_text(original)
        report = self.run_cli('--daylight', '--auto-location')
        installed = json.loads(location.read_text())
        self.assertTrue(installed['auto_location'])
        self.assertTrue(installed['custom'])
        self.assertEqual(installed['latitude'], 48.85)
        script = self.home/'data/jialing/daylight.py'
        self.assertTrue(script.is_file())
        unit = self.config/'systemd/user/jialing-daylight.service'
        self.assertIn(str(script), unit.read_text())
        self.run_cli('--restore', report['backup'])
        self.assertEqual(location.read_text(), original)
        self.assertFalse(script.exists())
        self.assertFalse(unit.exists())

    def test_local_wallpaper_is_installed_for_both_variants_and_restored(self):
        wallpaper = self.home/'city.jpg'
        wallpaper.write_bytes(b'local image')
        report = self.run_cli('--wallpaper', str(wallpaper))
        for theme in ('jialing', 'jialing-light'):
            self.assertEqual((self.config/'omarchy/themes'/theme/'backgrounds/city.jpg').read_bytes(), b'local image')
        self.run_cli('--restore', report['backup'])
        self.assertFalse((self.config/'omarchy/themes/jialing/backgrounds/city.jpg').exists())
