import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "themes/jialing/menu-theme.py"

# Only the two insertion sites matter to setup; real QML rendering is checked
# in the installed shell, rather than imitated by this fixture.
MENU = '''import QtQuick
// Personal customization
property int cardWidth: Math.min(root.dmenuActive ? Style.space(root.dmenuWidth) : ((root.activeMenu === "style.font") ? Style.space(520) : Style.space(300)), panel.width - Style.gapsOut * 2)
    BorderSurface {
      id: card
    }
'''


class MenuSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="jialing menu ")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.plugin = self.home / ".config/omarchy/plugins/tester.menu"
        self.upstream = self.home / "omarchy/shell/plugins/menu"
        self.upstream.mkdir(parents=True)
        (self.upstream / "Menu.qml").write_text(MENU)
        self.commands = self.home / "commands.jsonl"
        bin_dir = self.home / "bin"
        bin_dir.mkdir()
        command = bin_dir / "omarchy"
        command.write_text(
            f"#!{sys.executable}\n"
            "import os, sys, json, shutil\nfrom pathlib import Path\n"
            "home = Path.home()\n"
            "with (home / 'commands.jsonl').open('a') as f: f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "if sys.argv[1:] == ['plugin', 'clone', 'omarchy.menu']:\n"
            "    plugin = home / '.config/omarchy/plugins/tester.menu'\n"
            "    plugin.mkdir(parents=True)\n"
            "    shutil.copy(home / 'omarchy/shell/plugins/menu/Menu.qml', plugin / 'Menu.qml')\n"
            "    (plugin / 'manifest.json').write_text(json.dumps({'omarchy': {'clonedFrom': 'omarchy.menu'}}))\n"
        )
        command.chmod(0o755)
        self.env = dict(
            os.environ,
            HOME=str(self.home),
            USER="tester",
            XDG_CONFIG_HOME=str(self.home / ".config"),
            XDG_STATE_HOME=str(self.home / ".local/state"),
            OMARCHY_PATH=str(self.home / "omarchy"),
            PATH=str(bin_dir) + os.pathsep + os.environ["PATH"],
        )

    def run_setup(self):
        return subprocess.run(
            [sys.executable, str(SCRIPT)], env=self.env, capture_output=True, text=True
        )

    def test_clone_setup_preserves_source_and_repeated_setup_keeps_one_backup(self):
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        installed = (self.plugin / "Menu.qml").read_text()
        self.assertIn("// Personal customization", installed)
        self.assertIn('Color.shellValues["menu.width"]', installed)
        self.assertIn('Color.pickAlpha("menu.shadow-alpha", 0)', installed)
        self.assertIn("root.dmenuWidth", installed)
        self.assertIn("Style.space(520)", installed)
        self.assertEqual((self.upstream / "Menu.qml").read_text(), MENU)
        backups = list((self.home / ".local/state/jialing/menu-backups").glob("*/Menu.qml"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), MENU)
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.plugin / "Menu.qml").read_text(), installed)
        self.assertEqual(len(list(backups[0].parent.parent.glob("*/Menu.qml"))), 1)
        commands = [json.loads(line) for line in self.commands.read_text().splitlines()]
        self.assertEqual(commands.count(["plugin", "clone", "omarchy.menu"]), 1)
        self.assertEqual(commands[-2:], [["plugin", "enable", "tester.menu"], ["restart", "shell"]])

    def test_unknown_upstream_layout_is_rejected_before_cloning(self):
        (self.upstream / "Menu.qml").write_text("new upstream layout")
        result = self.run_setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Menu layout has changed", result.stderr)
        self.assertFalse(self.plugin.exists())
        self.assertFalse(self.commands.exists())

    def test_unrelated_local_plugin_is_not_overwritten_or_enabled(self):
        self.plugin.mkdir(parents=True)
        (self.plugin / "manifest.json").write_text('{"id": "tester.menu"}')
        (self.plugin / "Menu.qml").write_text("personal plugin")
        result = self.run_setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.plugin / "Menu.qml").read_text(), "personal plugin")
        self.assertFalse(self.commands.exists())
