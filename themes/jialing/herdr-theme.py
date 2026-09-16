#!/usr/bin/env python3
"""Apply the current Jialing Herdr palette without replacing other settings."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tomllib


def merge(original, palette):
    sections = re.split(r'(?m)(?=^\[)', original)
    kept = []
    accent = tomllib.loads(palette)['theme']['custom']['accent']
    for section in sections:
        header = section.splitlines()[0] if section else ''
        if re.match(r'^\[theme(?:\.[^\]]+)?\]\s*(?:#.*)?$', header):
            continue
        if header.strip() == '[ui]':
            section = re.sub(r'(?m)^accent\s*=.*\n?', '', section)
            section = section.replace('[ui]', f'[ui]\naccent = "{accent}"', 1)
        kept.append(section)
    result = ''.join(kept).rstrip() + '\n\n' + palette
    tomllib.loads(result)
    return result


def main():
    config = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
    state = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state')))
    # Read the committed current theme, avoiding stale hook arguments.
    name = (state / 'omarchy/current/theme.name').read_text().strip()
    if name not in ('jialing', 'jialing-light'):
        return
    path = config / 'herdr/config.toml'
    if not path.exists():
        return
    palette = (config / 'omarchy/themes' / name / 'herdr.toml').read_text()
    original = path.read_text()
    result = merge(original, palette)
    if result != original:
        backup = path.with_name('config.toml.before-jialing')
        if not backup.exists():
            shutil.copy2(path, backup)
        temporary = path.with_suffix('.jialing.tmp')
        temporary.write_text(result)
        temporary.chmod(path.stat().st_mode & 0o777)
        temporary.replace(path)
    # Reload live sessions without restarting panes. A stopped server is fine.
    status = subprocess.run(['herdr', 'server', 'reload-config'], capture_output=True, text=True)
    if status.returncode:
        print('Herdr palette saved; live reload unavailable: ' + status.stderr.strip())
    else:
        print('Applied Herdr palette: ' + name)


if __name__ == '__main__':
    main()
