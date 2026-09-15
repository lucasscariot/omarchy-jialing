#!/usr/bin/env python3
"""Switch between native Jialing variants at sunrise and sunset."""
import argparse
from datetime import datetime
import json
import math
import os
from pathlib import Path
import subprocess
import time
import urllib.request
from zoneinfo import ZoneInfo
from astral import Observer
from astral.sun import sunrise, sunset, elevation

THEMES = ('jialing', 'jialing-light')
LOCATION_TTL = 3600


def read_json(path):
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def validate_location(value):
    if not isinstance(value, dict):
        raise ValueError("Location must be a JSON object")
    for key, limit in (('latitude',90), ('longitude',180)):
        number = value.get(key)
        if isinstance(number, bool) or not isinstance(number, (float,int)) or not math.isfinite(number) or not -limit <= number <= limit:
            raise ValueError('Invalid or missing ' + key)
    try:
        ZoneInfo(value['timezone'])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('Invalid or missing IANA timezone') from error
    return {key:value[key] for key in ('latitude','longitude','timezone')} | {'city':str(value.get('city') or 'Configured location')}


def current_location(config, cache_path, refresh=False, force=False):
    if config.get('auto_location') is not True:
        return validate_location(config) | {'location_source':'configured'}
    cached = read_json(cache_path)
    now = time.time()
    checked = cached.get('checked_at',0)
    checked = checked if isinstance(checked,(float,int)) and math.isfinite(checked) else 0
    if refresh and (force or not 0 <= now - checked < LOCATION_TTL):
        try:
            request = urllib.request.Request('https://ipapi.co/json/', headers={'User-Agent':'JialingDaylight/1.0'})
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.loads(response.read(65536))
            cached['location'] = validate_location(payload)
            cached.pop('error',None)
        except (OSError, ValueError, KeyError, TypeError):
            cached['error'] = 'Location lookup failed; using saved location or configured fallback'
        cached['checked_at'] = now
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(cached))
        temporary.replace(cache_path)
    try:
        location = validate_location(cached.get('location',{}))
        return location | {'location_source':'cached ipapi.co', 'location_warning':cached.get('error')}
    except ValueError:
        return validate_location(config) | {'location_source':'configured fallback', 'location_warning':cached.get('error')}


def selection(location, now):
    observer = Observer(location['latitude'], location['longitude'])
    zone = ZoneInfo(location['timezone'])
    now = now.astimezone(zone)
    try:
        rise = sunrise(observer, now.date(), zone)
        setting = sunset(observer, now.date(), zone)
        day = rise <= now < setting
    except ValueError:
        rise = setting = None
        day = elevation(observer, now) > -0.833
    return {'theme':'jialing-light' if day else 'jialing',
            'sunrise':rise.isoformat() if rise else None,
            'sunset':setting.isoformat() if setting else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--status', action='store_true', help='Inspect schedule; no desktop or network changes by default')
    parser.add_argument('--refresh-location', action='store_true', help='Request an IP location refresh when auto_location is enabled')
    parser.add_argument('--now', help='ISO timestamp for inspection; requires --status')
    args = parser.parse_args()
    if args.now and not args.status:
        parser.error('--now requires --status')
    config_home = Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))
    state = Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))
    try:
        current = (state/'omarchy/current/theme.name').read_text().strip()
    except OSError:
        current = None
    if not args.status and current not in THEMES:
        return
    config = read_json(config_home/'omarchy/jialing-daylight.json')
    location = current_location(config, state/'omarchy/jialing-location.json', refresh=not args.status or args.refresh_location, force=args.refresh_location)
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(ZoneInfo(location['timezone']))
    if now.tzinfo is None:
        parser.error('--now must include a timezone offset')
    result = selection(location,now) | location | {'current_theme':current}
    result['should_change'] = current in THEMES and current != result['theme']
    if args.status:
        print(json.dumps(result,indent=2))
        return
    if not result['should_change']:
        return
    if subprocess.run(['hyprctl','monitors','-j'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        return
    # Theme command serializes competing changes using Omarchy's own lock.
    subprocess.run(['omarchy','theme','set',result['theme']], env=dict(os.environ,OMARCHY_THEME_SKIP_BACKGROUND='1'),check=True)
    print('Applied ' + result['theme'])


if __name__ == '__main__':
    try:
        main()
    except (OSError,ValueError,subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
