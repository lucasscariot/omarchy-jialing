"""Check that Herdr colors follow Jialing without replacing personal settings."""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "themes/jialing/herdr-theme.py"
SPEC = importlib.util.spec_from_file_location("jialing_herdr_theme", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class HerdrThemeTests(unittest.TestCase):
    def test_merge_is_reversible_and_preserves_unrelated_settings(self):
        original = (
            '[ui]\npane_gaps = false\n\n'
            '[theme]\nname = "catppuccin"\nauto_switch = true\n\n'
            '[theme.custom]\nsidebar_bg = "#123456"\ntext = "#eeeeee"\n\n'
            '[[keys.command]]\nkey = "prefix+x"\n'
        )
        palette = {
            "theme": {"name": "terminal", "auto_switch": False},
            "theme.custom": {"sidebar_bg": "#161618", "surface_dim": "#2A2A2F"},
        }
        applied = MODULE.merge(original, palette)
        self.assertEqual(MODULE.merge(applied, palette), applied)
        self.assertEqual(MODULE.merge(applied), original)
        parsed = tomllib.loads(applied)
        self.assertEqual(parsed["theme"]["custom"]["sidebar_bg"], "#161618")
        self.assertEqual(parsed["theme"]["custom"]["text"], "#eeeeee")

    def test_theme_switch_applies_and_removes_herdr_colors(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / "config"
            state = home / "state/omarchy/current"
            state.mkdir(parents=True)
            source = config / "omarchy/themes/jialing/herdr.toml"
            source.parent.mkdir(parents=True)
            source.write_bytes((ROOT / "themes/jialing/herdr.toml").read_bytes())
            target = config / "herdr/config.toml"
            target.parent.mkdir(parents=True)
            original = '[keys]\nprefix = "ctrl+space"\n\n[theme]\nname = "catppuccin"\n'
            target.write_text(original)
            fake_bin = home / "bin"
            fake_bin.mkdir()
            stub = fake_bin / "herdr"
            stub.write_text("#!/bin/sh\nexit 0\n")
            stub.chmod(0o755)
            env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(config),
                       XDG_STATE_HOME=str(home / "state"), PATH=str(fake_bin) + ":" + os.environ["PATH"])

            (state / "theme.name").write_text("jialing\n")
            subprocess.run([sys.executable, str(SCRIPT)], env=env, check=True)
            applied = tomllib.loads(target.read_text())
            self.assertEqual(applied["theme"]["name"], "terminal")
            self.assertEqual(applied["theme"]["custom"]["sidebar_bg"], "#161618")
            self.assertEqual(applied["keys"]["prefix"], "ctrl+space")

            (state / "theme.name").write_text("everforest\n")
            subprocess.run([sys.executable, str(SCRIPT)], env=env, check=True)
            self.assertEqual(target.read_text(), original)


if __name__ == "__main__":
    unittest.main()
