#!/usr/bin/env python3
"""Add theme-controlled width and shadow to a user-owned Omarchy menu clone."""

import getpass
import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

WIDTH = " : Style.space(300)), panel.width - Style.gapsOut * 2)"
THEMED_WIDTH = (
    ' : Style.space(Math.max(1, Number(Color.shellValues["menu.width"]) || 300))),'
    " panel.width - Style.gapsOut * 2)"
)
CARD = "    BorderSurface {\n      id: card\n"
SHADOW = """    // Jialing: optional shadow, disabled for themes without the token.
    RectangularShadow {
      anchors.fill: card
      radius: card.radius
      blur: 40
      spread: 2
      offset: Qt.vector2d(0, 12)
      color: Qt.alpha("#000000", Color.pickAlpha("menu.shadow-alpha", 0))
      visible: color.a > 0
    }

"""
APP_LIBRARY = "  readonly property var appLibrary: root.shell ? root.shell.appLibrary : null"
APP_LIBRARY_FALLBACK = """  // Jialing: some Omarchy versions omit the app service from menu clones.
  readonly property var appLibrary: root.shell && root.shell.appLibrary
    ? root.shell.appLibrary : fallbackAppLibrary.item
  Loader {
    id: fallbackAppLibrary
    active: !!root.shell && !root.shell.appLibrary
    sourceComponent: Component { Services.AppLibrary { } }
    onLoaded: if (root.providersLoaded["apps"]) root.mergeAppRows()
  }"""


def themed_menu(source):
    """Refuse unknown layouts; preserve other changes and allow repeated runs."""
    if APP_LIBRARY_FALLBACK not in source:
        if source.count(APP_LIBRARY) != 1:
            raise ValueError("Menu layout has changed; cannot find the application library")
        source = source.replace(APP_LIBRARY, APP_LIBRARY_FALLBACK, 1)
    if "import qs.services as Services\n" not in source:
        source = "import qs.services as Services\n" + source
    if THEMED_WIDTH in source and SHADOW in source and "import QtQuick.Effects\n" in source:
        return source
    if source.count(WIDTH) != 1 or source.count(CARD) != 1:
        raise ValueError(
            "Menu layout has changed; refusing to overwrite it. Review Menu.qml first."
        )
    if "import QtQuick.Effects\n" not in source:
        if source.count("import QtQuick\n") != 1:
            raise ValueError("Cannot find the menu's QtQuick import")
        source = source.replace("import QtQuick\n", "import QtQuick\nimport QtQuick.Effects\n", 1)
    return source.replace(WIDTH, THEMED_WIDTH, 1).replace(CARD, SHADOW + CARD, 1)


def main():
    config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    # Omarchy's clone command currently uses the standard home paths.
    if config != Path.home() / ".config":
        raise ValueError("Menu setup requires the standard ~/.config location")
    plugin_id = f"{os.environ.get('USER') or getpass.getuser()}.menu"
    plugin = config / "omarchy/plugins" / plugin_id
    target = plugin / "Menu.qml"
    if plugin.exists():
        manifest = json.loads((plugin / "manifest.json").read_text())
        if manifest.get("omarchy", {}).get("clonedFrom") != "omarchy.menu":
            raise ValueError(f"{plugin} is not a clone of omarchy.menu")
    else:
        upstream = Path(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy"))
        themed_menu((upstream / "shell/plugins/menu/Menu.qml").read_text())
        subprocess.run(["omarchy", "plugin", "clone", "omarchy.menu"], check=True)
    if target.is_symlink():
        raise ValueError(f"Refusing symlink destination: {target}")
    original = target.read_text()
    updated = themed_menu(original)
    if updated != original:
        state = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
        backup = state / "jialing/menu-backups" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup.mkdir(parents=True, mode=0o700)
        (backup / "Menu.qml").write_bytes(target.read_bytes())
        print(f"Original menu: {backup / 'Menu.qml'}", flush=True)
        with tempfile.NamedTemporaryFile(dir=plugin, mode="w", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(updated)
        try:
            temporary.chmod(target.stat().st_mode & 0o777)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    subprocess.run(["omarchy", "plugin", "enable", plugin_id], check=True)
    subprocess.run(["omarchy", "restart", "shell"], check=True)
    print(f"Enabled {plugin_id}: width and shadow now follow the active theme.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
