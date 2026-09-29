"""Exercise the one-line entry point with a local substitute for GitHub."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="jialing bootstrap ")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
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
            TMPDIR=str(self.home),
        )

    def run_cli(self, *args):
        return subprocess.run(
            ["bash", str(ROOT / "install.sh"), *args], env=self.env, capture_output=True, text=True
        )

    def test_one_line_install_and_restore(self):
        result = self.run_cli("--no-apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = next(json.loads(line) for line in result.stdout.splitlines() if line.startswith("{"))
        self.assertEqual(report["theme"], "jialing")
        self.assertTrue((self.home / "config/omarchy/themes/jialing/colors.toml").exists())
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
