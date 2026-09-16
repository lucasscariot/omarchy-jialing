"""Exercise the one-line entry point with a local substitute for GitHub."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from icon_fixture import installed_icons

ROOT = Path(__file__).resolve().parents[1]


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="jialing bootstrap ")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        installed_icons(self.home / "data")
        self.bin = self.home / "bin"
        self.bin.mkdir()
        git = self.bin / "git"
        git.write_text(
            "#!"
            + sys.executable
            + "\nimport shutil, sys\nshutil.copytree("
            + repr(str(ROOT))
            + ', sys.argv[-1], ignore=shutil.ignore_patterns(".git", "__pycache__"))\n'
        )
        git.chmod(0o755)
        self.env = dict(
            os.environ,
            HOME=str(self.home),
            PATH=str(self.bin) + ":" + os.environ["PATH"],
            XDG_CONFIG_HOME=str(self.home / "config"),
            XDG_STATE_HOME=str(self.home / "state"),
            XDG_DATA_HOME=str(self.home / "data"),
            XDG_CACHE_HOME=str(self.home / "cache"),
            TMPDIR=str(self.home),
        )

    def run_cli(self, *args):
        return subprocess.run(
            ["bash", str(ROOT / "install.sh"), *args], env=self.env, capture_output=True, text=True
        )

    def test_one_line_install_forwards_options_and_supports_restore(self):
        wallpaper = self.home / "city view.jpg"
        wallpaper.write_bytes(b"local wallpaper")
        result = self.run_cli("--no-apply", "--variant", "light", "--wallpaper", str(wallpaper))
        self.assertEqual(result.returncode, 0, result.stderr)
        report = next(
            json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")
        )
        for theme in ("jialing", "jialing-light"):
            self.assertTrue((self.home / "config/omarchy/themes" / theme / "colors.toml").exists())
        result = self.run_cli("--restore", report["backup"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.home / "config/omarchy/themes/jialing/colors.toml").exists())
        self.assertFalse(list(self.home.glob("jialing-download.*")))

    def test_failed_download_cleans_up_and_does_not_touch_settings(self):
        (self.bin / "git").write_text("#!/bin/bash\nexit 23\n")
        result = self.run_cli("--no-apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.home / "config").exists())
        self.assertFalse(list(self.home.glob("jialing-download.*")))

    def test_apply_checks_compatibility_before_downloading(self):
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Lua Hyprland", result.stderr)
        self.assertFalse((self.home / "config/omarchy/themes").exists())
        self.assertFalse(list(self.home.glob("jialing-download.*")))

    def test_update_keeps_current_light_variant_and_personal_files(self):
        current = self.home / "state/omarchy/current/theme.name"
        current.parent.mkdir(parents=True)
        current.write_text("jialing-light")
        config = self.home / "config"
        (config / "hypr").mkdir(parents=True)
        (config / "hypr/hyprland.lua").write_text("-- user config")
        personal = config / "omarchy/themes/jialing/backgrounds/personal.jpg"
        personal.parent.mkdir(parents=True)
        personal.write_bytes(b"keep me")
        command = self.bin / "omarchy"
        command.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$HOME/applied"\n')
        command.chmod(0o755)
        for _ in range(2):
            result = self.run_cli()
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            (self.home / "applied").read_text().splitlines(),
            ["theme set jialing-light", "theme set jialing-light"],
        )
        self.assertEqual(personal.read_bytes(), b"keep me")

    def test_daylight_prepares_dependencies_and_activates_only_when_applying(self):
        # Substitute only dependency provisioning and the desktop service manager.
        python = self.bin / "python3"
        python.write_text(
            "#!"
            + sys.executable
            + "\n"
            + """import os, pathlib, shutil, subprocess, sys
with open(pathlib.Path.home()/'python-calls', 'a') as stream:
    stream.write(repr(sys.argv[1:])+'\\n')
if sys.argv[1:3] == ['-m', 'venv']:
    target = pathlib.Path(sys.argv[3])/'bin/python'
    target.parent.mkdir(parents=True)
    shutil.copy2(__file__, target)
elif sys.argv[1:3] == ['-m', 'pip']:
    pass
else:
    raise SystemExit(subprocess.call([sys.executable, *sys.argv[1:]]))
"""
        )
        python.chmod(0o755)
        service = self.bin / "systemctl"
        service.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$HOME/services"\n')
        service.chmod(0o755)
        omarchy = self.bin / "omarchy"
        omarchy.write_text("#!/bin/bash\nexit 0\n")
        omarchy.chmod(0o755)
        (self.home / "config/hypr").mkdir(parents=True)
        (self.home / "config/hypr/hyprland.lua").write_text("-- supported config")
        result = self.run_cli("--daylight", "--auto-location", "--no-apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.home / "services").exists())
        self.assertTrue((self.home / "data/jialing/daylight.py").exists())
        settings = json.loads((self.home / "config/omarchy/jialing-daylight.json").read_text())
        self.assertTrue(settings["auto_location"])
        result = self.run_cli("--daylight", "--auto-location")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            (self.home / "services").read_text().splitlines(),
            [
                "--user daemon-reload",
                "--user enable --now jialing-daylight.timer",
                "--user start jialing-daylight.service",
            ],
        )
        calls = (self.home / "python-calls").read_text()
        self.assertIn("'-m', 'venv'", calls)
        self.assertIn("'-m', 'pip', 'install'", calls)
