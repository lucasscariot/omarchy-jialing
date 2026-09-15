#!/usr/bin/env python3
"""Install the native theme and apply its companion font/terminal profile."""
from datetime import datetime
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET


def main():
    source = Path(__file__).resolve().parent
    config = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
    target = config / 'omarchy/themes/jialing'
    fonts = subprocess.check_output(['fc-list', '-f', '%{family}\n'], text=True)
    missing = [font for font in ('Inter', 'iA Writer Mono S') if font not in fonts]
    if missing:
        raise SystemExit('Install these fonts first: ' + ', '.join(missing) + '. See README.md.')
    backup = config / 'omarchy/backups' / ('jialing-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True)

    def save(path, name):
        if path.exists():
            shutil.copy2(path, backup / name)

    if target.resolve() != source:
        if target.exists():
            shutil.copytree(target, backup / 'theme')
        shutil.copytree(source, target, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('.git', '*.bak*', '__pycache__'))

    fontconfig = config / 'fontconfig/fonts.conf'
    save(fontconfig, 'fonts.conf')
    tree = ET.parse(fontconfig) if fontconfig.exists() else ET.ElementTree(ET.Element('fontconfig'))
    # Replace only this profile's rules on subsequent runs.
    for child in list(tree.getroot()):
        if child.get('target') == 'pattern' and child.find("test[@name='family']/string") is not None:
            families = [node.text for node in child.findall("edit[@name='family']/string")]
            if families in (['Inter'], ['iA Writer Mono S']):
                tree.getroot().remove(child)
    for child in ET.parse(target / 'profile/fonts.conf').getroot():
        tree.getroot().append(child)
    fontconfig.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(tree)
    tree.write(fontconfig, encoding='utf-8', xml_declaration=True)

    ghostty = config / 'ghostty/config'
    save(ghostty, 'ghostty-config')
    text = ghostty.read_text() if ghostty.exists() else ''
    # Theme now owns these appearance properties; retain shortcuts and behavior.
    keys = {'font-family', 'font-style', 'font-size', 'background-opacity', 'window-padding-x', 'window-padding-y'}
    lines = [line for line in text.splitlines() if line.partition('=')[0].strip() not in keys]
    include = 'config-file = ?"~/.local/state/omarchy/current/theme/ghostty.conf"'
    if not any('current/theme/ghostty.conf' in line and not line.lstrip().startswith('#') for line in lines):
        lines.insert(0, include)
    ghostty.parent.mkdir(parents=True, exist_ok=True)
    ghostty.write_text('\n'.join(lines) + '\n')
    for key, value in [('font-name', 'Inter 11'), ('document-font-name', 'Inter 11'), ('monospace-font-name', 'iA Writer Mono S 10')]:
        old = subprocess.check_output(['gsettings', 'get', 'org.gnome.desktop.interface', key], text=True)
        (backup / (key + '.txt')).write_text(old)
        subprocess.run(['gsettings', 'set', 'org.gnome.desktop.interface', key, value], check=True)
    subprocess.run(['omarchy', 'theme', 'set', 'jialing'], check=True)
    subprocess.run(['ghostty', '+validate-config'], check=True)
    subprocess.run(['omarchy', 'restart', 'shell'], check=True)
    print('Applied Jialing. Backups: ' + str(backup))


if __name__ == '__main__':
    main()
