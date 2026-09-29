#!/usr/bin/env python3
"""Install Jialing's Omarchy theme and its optional Herdr theme hook."""

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
THEME = "jialing"
ASSETS = (
    "colors.toml",
    "shell.toml",
    "hyprland.lua",
    "ghostty.conf",
    "herdr.toml",
    "herdr-theme.py",
    "preview.png",
)


def location_root(variable, fallback):
    return Path(os.environ.get(variable, str(Path.home() / fallback))).expanduser().absolute()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data, mode=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(data)
    try:
        if mode is not None:
            temporary.chmod(mode)
        elif path.exists():
            temporary.chmod(path.stat().st_mode & 0o777)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def check_destinations(files):
    # Preflight every destination before changing files.
    for path in files:
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
            raise ValueError("Refusing symlink destination: " + str(path))
        if path.exists() and not path.is_file():
            raise ValueError("Expected a file: " + str(path))


def write_files(files, state, executables=()):
    check_destinations(files)
    backup = state / "jialing/backups" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup.mkdir(parents=True, mode=0o700)
    entries = []
    for index, (path, data) in enumerate(files.items()):
        old = path.read_bytes() if path.exists() else None
        old_mode = path.stat().st_mode & 0o777 if old is not None else None
        if old is not None:
            (backup / str(index)).write_bytes(old)
        entries.append(
            {
                "path": str(path),
                "old": str(index) if old is not None else None,
                "installed_sha256": digest(data),
                "old_mode": old_mode,
                "installed_mode": 0o755
                if path in executables
                else (old_mode if old_mode is not None else 0o600),
            }
        )
    (backup / "manifest.json").write_text(json.dumps(entries, indent=2))
    completed = []
    try:
        for entry, (path, data) in zip(entries, files.items()):
            atomic_write(path, data, entry["installed_mode"])
            completed.append(entry)
    except OSError:
        for entry in reversed(completed):
            path = Path(entry["path"])
            if entry["old"] is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, (backup / entry["old"]).read_bytes(), entry["old_mode"])
        raise
    return backup


def restore(backup):
    entries = json.loads((backup / "manifest.json").read_text())
    # Refuse the whole restore if any installed file has since changed.
    for entry in entries:
        path = Path(entry["path"])
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
            raise ValueError("Refusing symlink restore: " + str(path))
        if not path.is_file() or digest(path.read_bytes()) != entry["installed_sha256"]:
            raise ValueError("File changed since installation: " + str(path))
        if "installed_mode" in entry and path.stat().st_mode & 0o777 != entry["installed_mode"]:
            raise ValueError("File permissions changed since installation: " + str(path))
    originals = {
        entry["path"]: (backup / entry["old"]).read_bytes()
        for entry in entries
        if entry["old"] is not None
    }
    for entry in entries:
        path = Path(entry["path"])
        if entry["old"] is None:
            path.unlink()
        else:
            atomic_write(path, originals[entry["path"]], entry.get("old_mode"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-apply", action="store_true", help="Install files without switching themes")
    parser.add_argument("--restore", type=Path, help="Restore a previous installation backup")
    args = parser.parse_args()
    if args.restore:
        restore(args.restore)
        print(json.dumps({"restored": str(args.restore)}))
        return

    config = location_root("XDG_CONFIG_HOME", ".config")
    state = location_root("XDG_STATE_HOME", ".local/state")
    target = config / "omarchy/themes" / THEME
    files = {target / name: (ROOT / "themes" / THEME / name).read_bytes() for name in ASSETS}
    hook = config / "omarchy/hooks/theme-set.d/jialing-herdr"
    files[hook] = (ROOT / "themes" / THEME / "herdr-theme-hook").read_bytes()
    backup = write_files(files, state, executables={hook})
    print(json.dumps({"backup": str(backup), "theme": THEME}), flush=True)
    if not args.no_apply:
        subprocess.run(["omarchy", "theme", "set", THEME], check=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
