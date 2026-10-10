"""Keep secondary terminal text legible on Jialing's dark surfaces."""

import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def luminance(color):
    channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast(a, b):
    light, dark = sorted((luminance(a), luminance(b)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


class ContrastTests(unittest.TestCase):
    def test_secondary_terminal_text_is_legible_on_dark_surfaces(self):
        colors = tomllib.loads((ROOT / 'colors.toml').read_text())
        muted = colors['muted']
        self.assertGreaterEqual(contrast(muted, colors['background']), 4.5)
        self.assertGreaterEqual(contrast(muted, colors['lighter_background']), 4.5)

    def test_body_text_and_accent_stay_legible(self):
        colors = tomllib.loads((ROOT / 'colors.toml').read_text())
        self.assertGreaterEqual(contrast(colors['foreground'], colors['background']), 10)
        self.assertGreaterEqual(contrast(colors['accent'], colors['background']), 7)
        self.assertGreaterEqual(contrast(colors['bright_foreground'], colors['selection']), 7)
        for name in ('red', 'yellow', 'green', 'cyan', 'blue', 'magenta'):
            self.assertGreaterEqual(contrast(colors[name], colors['background']), 4.5, name)
