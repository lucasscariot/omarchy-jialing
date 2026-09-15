#!/usr/bin/env python3
"""Select the native Jialing variant using local solar calculations."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
from zoneinfo import ZoneInfo
from astral import Observer
from astral.sun import sunrise, sunset, elevation


def current_location(config, cache_path):
    if not config.get('auto_location', False):
        return config
    try:
        cached = json.loads(cache_path.read_text())
    except (OSError, ValueError):
        cached = {}
    now = time.time()
    if now - cached.get('checked_at', 0) >= 3600:
        try:
            request = urllib.request.Request('https://ipapi.co/json/', headers={'User-Agent': 'JialingDaylight/1.0'})
            with urllib.request.urlopen(request, timeout=8) as response:
                data = json.load(response)
            latitude, longitude = float(data['latitude']), float(data['longitude'])
            if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
                raise ValueError('Invalid coordinates')
            ZoneInfo(data['timezone'])
            cached['location'] = {'city': data.get('city') or 'Detected location',
                                  'latitude': latitude, 'longitude': longitude,
                                  'timezone': data['timezone']}
            cached.pop('error', None)
        except (OSError, ValueError, KeyError, TypeError):
            cached['error'] = 'Location lookup unavailable; using last known or configured fallback'
        cached['checked_at'] = now
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(cached))
        temporary.replace(cache_path)
    return dict(config, **cached.get('location', {}), location_source='ipapi.co' if cached.get('location') else 'configured fallback')


def selection(config, now):
    observer = Observer(config['latitude'], config['longitude'])
    zone = ZoneInfo(config['timezone'])
    now = now.astimezone(zone)
    try:
        rise = sunrise(observer, now.date(), zone)
        setting = sunset(observer, now.date(), zone)
        day = rise <= now < setting
    except ValueError:
        # Polar day/night: the sun may never cross the horizon today.
        rise = setting = None
        day = elevation(observer, now) > -0.833
    return {'theme': 'jialing-light' if day else 'jialing',
            'sunrise': rise.isoformat() if rise else None,
            'sunset': setting.isoformat() if setting else None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--status', action='store_true', help='Show today’s schedule without switching')
    args = parser.parse_args()
    config_home = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
    config = json.loads((config_home / 'omarchy/jialing-daylight.json').read_text())
    state = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state')))
    config = current_location(config, state / 'omarchy/jialing-location.json')
    result = selection(config, datetime.now(ZoneInfo(config['timezone'])))
    if args.status:
        print(json.dumps(dict(result, city=config['city'], location_source=config.get('location_source', 'configured')), indent=2))
        return
    state = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state')))
    current = (state / 'omarchy/current/theme.name').read_text().strip()
    # Choosing an unrelated theme is an intentional opt-out.
    if current not in ('jialing', 'jialing-light') or current == result['theme']:
        return
    if subprocess.run(['hyprctl', 'monitors', '-j'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        return
    env = dict(os.environ, OMARCHY_THEME_SKIP_BACKGROUND='1')
    subprocess.run(['omarchy', 'theme', 'set', result['theme']], env=env, check=True)
    print('Applied ' + result['theme'], flush=True)


if __name__ == '__main__':
    main()
