"""Check that Jialing installs its theme and Herdr theme-change hook."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = {"colors.toml", "shell.toml", "hyprland.lua", "ghostty.conf", "herdr.toml", "herdr-theme.py", "preview.png"}


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="jialing test ")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.config = self.home / "config"
        self.env = dict(
            os.environ,
            HOME=str(self.home),
            XDG_CONFIG_HOME=str(self.config),
            XDG_STATE_HOME=str(self.home / "state"),
        )

    def run_cli(self, *args, success=True):
        result = subprocess.run(
            [sys.executable, str(ROOT / "install.py"), "--no-apply", *args],
            env=self.env,
            capture_output=True,
            text=True,
        )
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        return result

    def test_install_preserves_existing_wallpaper_and_writes_theme_assets(self):
        target = self.config / "omarchy/themes/jialing"
        background = target / "backgrounds/personal.jpg"
        background.parent.mkdir(parents=True)
        background.write_bytes(b"personal wallpaper")
        report = self.run_cli()
        self.assertEqual(report["theme"], "jialing")
        self.assertEqual({p.name for p in target.iterdir() if p.is_file()}, ASSETS)
        self.assertEqual(background.read_bytes(), b"personal wallpaper")
        self.assertFalse((self.config / "omarchy/themes/jialing-light").exists())
        self.assertTrue((self.config / "omarchy/hooks/theme-set.d/jialing-herdr").stat().st_mode & 0o111)
        self.assertTrue(Path(report["backup"]).is_dir())

    def test_restore_recovers_previous_file_and_removes_new_assets(self):
        original = self.config / "omarchy/themes/jialing/colors.toml"
        original.parent.mkdir(parents=True)
        original.write_text("old palette")
        report = self.run_cli()
        self.run_cli("--restore", report["backup"])
        self.assertEqual(original.read_text(), "old palette")
        self.assertFalse((self.config / "omarchy/themes/jialing/shell.toml").exists())
        self.assertFalse((self.config / "omarchy/hooks/theme-set.d/jialing-herdr").exists())

    def test_restore_refuses_later_edits(self):
        report = self.run_cli()
        asset = self.config / "omarchy/themes/jialing/colors.toml"
        asset.write_text("my later changes")
        self.run_cli("--restore", report["backup"], success=False)
        self.assertEqual(asset.read_text(), "my later changes")

    def test_symlink_destination_is_rejected_before_any_write(self):
        outside = self.home / "outside"
        outside.mkdir()
        target = self.config / "omarchy/themes/jialing"
        target.parent.mkdir(parents=True)
        target.symlink_to(outside, target_is_directory=True)
        self.run_cli(success=False)
        self.assertEqual(list(outside.iterdir()), [])

    def test_incomplete_backup_refuses_restore_before_any_change(self):
        original = self.config / "omarchy/themes/jialing/colors.toml"
        original.parent.mkdir(parents=True)
        original.write_text("old palette")
        report = self.run_cli()
        backup = Path(report["backup"])
        entries = json.loads((backup / "manifest.json").read_text())
        for entry in entries:
            if entry["old"] is not None:
                (backup / entry["old"]).unlink()
        self.run_cli("--restore", str(backup), success=False)
        self.assertNotEqual(original.read_text(), "old palette")

    def test_preview_is_installed(self):
        self.run_cli()
        self.assertEqual(
            (self.config / "omarchy/themes/jialing/preview.png").read_bytes(),
            (ROOT / "themes/jialing/preview.png").read_bytes(),
        )
