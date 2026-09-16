"""Provision a pinned, user-local WhiteSur dependency for both Jialing variants."""

import hashlib
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path

VERSION = "2026-09-10"
COMMIT = "73d8040da51a9ed74e47c7366e7e9ff437601a5c"
SHA256 = "96661649071d8a9664b40d42abea75286175234473106156e9a4b25f54e6cb0c"
URL = f"https://codeload.github.com/vinceliuice/WhiteSur-icon-theme/tar.gz/{COMMIT}"
NAME = f"Jialing-WhiteSur-{VERSION}"
NAMES = (NAME, NAME + "-light", NAME + "-dark")


def ensure_icons(data, cache):
    """Install once; never overwrite another icon theme or require root."""
    destination = data / "icons"
    targets = [destination / name for name in NAMES]
    for target in targets:
        if target.is_symlink() or any(parent.is_symlink() for parent in target.parents):
            raise ValueError(f"Refusing symlink icon destination: {target}")
    if all((target / "index.theme").is_file() for target in targets):
        return
    if any(target.exists() for target in targets):
        raise ValueError(
            f"Incomplete WhiteSur installation in {destination}. "
            f"Move the {NAME}* directories aside and retry."
        )

    archive = cache / "jialing" / f"whitesur-{COMMIT}.tar.gz"
    if archive.is_file():
        payload = archive.read_bytes()
    else:
        with urllib.request.urlopen(URL, timeout=60) as response:
            payload = response.read()
    if hashlib.sha256(payload).hexdigest() != SHA256:
        raise ValueError(f"WhiteSur checksum mismatch. Remove {archive} and retry.")
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_bytes(payload)

    # Upstream's installer has unquoted paths. Use a whitespace-free staging
    # location, then move its relative symlinks intact into the user's data path.
    with tempfile.TemporaryDirectory(prefix="jialing-icons-", dir="/tmp") as temporary:
        staging = Path(temporary)
        with tarfile.open(archive) as source:
            source.extractall(staging, filter="data")
        source = staging / f"WhiteSur-icon-theme-{COMMIT}"
        output = staging / "installed"
        output.mkdir()
        subprocess.run(
            ["bash", str(source / "install.sh"), "--dest", str(output), "--name", NAME],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        for name in NAMES:
            theme = output / name
            if not (theme / "index.theme").is_file():
                raise ValueError(f"WhiteSur did not produce {name}")
            for attribution in ("COPYING", "AUTHORS"):
                shutil.copy2(source / attribution, theme / attribution)
            (theme / "JIALING-SOURCE.txt").write_text(
                f"WhiteSur {VERSION}\nSource: {URL}\nSHA256: {SHA256}\n"
                "Installed with upstream's default blue folders and regular panel icons.\n"
            )
        destination.mkdir(parents=True, exist_ok=True)
        # Prepare on the destination filesystem before publishing directories.
        # A copy failure must not leave a half-populated icon theme behind.
        with tempfile.TemporaryDirectory(prefix=".jialing-icons-", dir=destination) as transfer:
            ready = Path(transfer)
            for name in NAMES:
                shutil.copytree(output / name, ready / name, symlinks=True)
            installed = []
            try:
                for name, target in zip(NAMES, targets):
                    if target.exists() or target.is_symlink():
                        raise ValueError(f"Icon destination appeared during installation: {target}")
                    (ready / name).rename(target)
                    installed.append(target)
            except (OSError, ValueError):
                for target in reversed(installed):
                    shutil.rmtree(target)
                raise
