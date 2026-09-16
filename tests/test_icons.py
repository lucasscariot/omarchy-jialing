import hashlib
import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import icons


def source_archive():
    """Small stand-in for the pinned upstream source and installer."""
    script = """set -eu
dest=$2
name=$4
mkdir -p "$dest/$name/places"
printf '<svg/>' > "$dest/$name/places/folder.svg"
for suffix in '' '-light' '-dark'; do
  mkdir -p "$dest/$name$suffix"
  printf '[Icon Theme]\\nName=%s\\n' "$name$suffix" > "$dest/$name$suffix/index.theme"
done
ln -s "../$name/places" "$dest/$name-light/places"
ln -s "../$name/places" "$dest/$name-dark/places"
"""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, text in {"install.sh": script, "COPYING": "GPL-3.0", "AUTHORS": "Vince"}.items():
            info = tarfile.TarInfo(f"WhiteSur-icon-theme-{icons.COMMIT}/{name}")
            payload = text.encode()
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    return buffer.getvalue()


class IconTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="jialing icon test ")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.data, self.cache = root / "data with spaces", root / "cache"
        self.payload = source_archive()
        self.checksum = patch.object(icons, "SHA256", hashlib.sha256(self.payload).hexdigest())
        self.checksum.start()
        self.addCleanup(self.checksum.stop)

    def install(self):
        with patch.object(icons.urllib.request, "urlopen", return_value=io.BytesIO(self.payload)):
            icons.ensure_icons(self.data, self.cache)

    def test_install_keeps_relative_links_licenses_and_unrelated_icon_themes(self):
        other = self.data / "icons/WhiteSur/index.theme"
        other.parent.mkdir(parents=True)
        other.write_text("personal version")
        self.install()
        self.assertEqual(other.read_text(), "personal version")
        for name in icons.NAMES:
            theme = self.data / "icons" / name
            self.assertTrue((theme / "index.theme").is_file())
            self.assertEqual((theme / "places/folder.svg").read_text(), "<svg/>")
            self.assertEqual((theme / "COPYING").read_text(), "GPL-3.0")
            self.assertIn(icons.COMMIT, (theme / "JIALING-SOURCE.txt").read_text())
        with patch.object(icons.urllib.request, "urlopen", side_effect=AssertionError("network")):
            icons.ensure_icons(self.data, self.cache)

    def test_cached_archive_supports_offline_install(self):
        archive = self.cache / "jialing" / f"whitesur-{icons.COMMIT}.tar.gz"
        archive.parent.mkdir(parents=True)
        archive.write_bytes(self.payload)
        with patch.object(icons.urllib.request, "urlopen", side_effect=AssertionError("network")):
            icons.ensure_icons(self.data, self.cache)
        self.assertTrue((self.data / "icons" / icons.NAME / "index.theme").is_file())

    def test_checksum_failure_cannot_execute_source_or_install_icons(self):
        with patch.object(icons.urllib.request, "urlopen", return_value=io.BytesIO(b"corrupt")):
            with patch.object(icons.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    icons.ensure_icons(self.data, self.cache)
                run.assert_not_called()
        self.assertFalse(self.data.exists())

    def test_partial_existing_install_is_preserved_and_refused(self):
        target = self.data / "icons" / icons.NAME
        target.mkdir(parents=True)
        (target / "personal.svg").write_text("custom")
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            icons.ensure_icons(self.data, self.cache)
        self.assertEqual((target / "personal.svg").read_text(), "custom")

    def test_upstream_failure_leaves_no_installed_theme(self):
        with patch.object(icons.urllib.request, "urlopen", return_value=io.BytesIO(self.payload)):
            with patch.object(icons.subprocess, "run", side_effect=OSError("install failed")):
                with self.assertRaisesRegex(OSError, "install failed"):
                    icons.ensure_icons(self.data, self.cache)
        self.assertFalse(self.data.exists())

    def test_copy_failure_does_not_publish_partial_icon_themes(self):
        with patch.object(icons.urllib.request, "urlopen", return_value=io.BytesIO(self.payload)):
            with patch.object(icons.shutil, "copytree", side_effect=OSError("disk full")):
                with self.assertRaisesRegex(OSError, "disk full"):
                    icons.ensure_icons(self.data, self.cache)
        self.assertEqual(list((self.data / "icons").iterdir()), [])
