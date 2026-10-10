"""Keep Jialing's theme files well formed and its palette coherent."""

import re
import shutil
import subprocess
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_SECTIONS = {
    "bar", "hyprland", "controls", "spacing", "font", "popups", "tooltip",
    "notifications", "launcher", "menu", "polkit", "lock", "image-picker",
}
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
GRADIENT_STOP = re.compile(r"^rgba?\([0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?\)$")
WIDTH = re.compile(r"^\d+( \d+){0,3}$")


def is_color(value):
    if HEX.match(value):
        return True
    parts = value.split()
    stops = [part for part in parts if not part.endswith("deg")]
    return bool(stops) and all(GRADIENT_STOP.match(part) for part in stops)


class ThemeFileTests(unittest.TestCase):
    def setUp(self):
        self.colors = tomllib.loads((ROOT / "colors.toml").read_text())
        self.shell = tomllib.loads((ROOT / "shell.toml").read_text())

    def test_palette_defines_every_key_the_templates_read(self):
        required = {
            "mode", "accent", "selection", "muted", "background", "dark_background",
            "darker_background", "lighter_background", "foreground", "dark_foreground",
            "light_foreground", "bright_foreground", "red", "yellow", "orange", "green",
            "cyan", "blue", "magenta", "brown", "bright_red", "bright_yellow",
            "bright_green", "bright_cyan", "bright_blue", "bright_magenta",
        }
        self.assertEqual(required - set(self.colors), set())
        for key, value in self.colors.items():
            if key == "mode":
                continue
            self.assertTrue(is_color(value), key)

    def test_focus_gradient_is_shared_by_hyprland_and_the_shell(self):
        gradient = self.colors["hyprland_active_border"]
        self.assertEqual(self.shell["hyprland"]["active-border"], gradient)
        lua = (ROOT / ".local-theme/hyprland.lua").read_text()
        for stop in gradient.split():
            if stop.endswith("deg"):
                continue
            self.assertIn(stop, lua)
        self.assertIn(self.colors["hyprland_inactive_border"], lua)

    def test_shell_surfaces_cover_the_template_and_use_valid_tokens(self):
        self.assertEqual(TEMPLATE_SECTIONS - set(self.shell), set())
        references = {"hyprland.active-border", "hyprland.active-border-foreground"}
        for section, values in self.shell.items():
            for key, value in values.items():
                if key.endswith("-alpha") or key == "scale":
                    self.assertTrue(0 <= value <= 1, f"{section}.{key}")
                elif key.endswith("-width") or key in ("size-horizontal", "size-vertical", "base-size"):
                    if isinstance(value, str):
                        self.assertTrue(WIDTH.match(value), f"{section}.{key}")
                    else:
                        self.assertGreaterEqual(value, 0, f"{section}.{key}")
                elif isinstance(value, str):
                    self.assertTrue(is_color(value) or value in references, f"{section}.{key} = {value}")

    def test_accent_matches_the_amber_gradient_stop_everywhere(self):
        accent = self.colors["accent"]
        self.assertEqual(self.colors["orange"], accent)
        self.assertEqual(self.shell["notifications"]["countdown"], accent)
        self.assertEqual(self.shell["menu"]["selected-text"], accent)
        self.assertEqual(self.shell["launcher"]["selected-text"], accent)
        herdr = tomllib.loads((ROOT / ".local-theme/herdr.toml").read_text())
        self.assertEqual(herdr["theme"]["custom"]["accent"], accent)
        self.assertEqual(herdr["theme"]["custom"]["red"], self.colors["red"])

    def test_hyprland_appearance_compiles(self):
        if not shutil.which("luac"):
            self.skipTest("luac is not installed")
        subprocess.run(["luac", "-p", str(ROOT / ".local-theme/hyprland.lua")], check=True)

    def test_installed_theme_ships_icons_and_a_wallpaper(self):
        self.assertEqual((ROOT / "icons.theme").read_text().strip(), "Yaru-yellow")
        wallpapers = [p for p in (ROOT / "backgrounds").iterdir() if p.suffix in (".jpg", ".png", ".webp")]
        self.assertTrue(wallpapers)
