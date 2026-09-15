#!/usr/bin/env python3
"""Install both native Jialing variants without replacing personal settings."""

import argparse
import configparser
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
THEMES = ("jialing", "jialing-light")
ASSETS = ("colors.toml", "shell.toml", "hyprland.lua", "ghostty.conf")


def location_root(variable, fallback):
    return Path(os.environ.get(variable, str(Path.home() / fallback))).expanduser().absolute()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(data)
    try:
        if path.exists():
            temporary.chmod(path.stat().st_mode & 0o777)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def write_files(files, state):
    # Preflight the entire set before changing any destination.
    for path in files:
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
            raise ValueError("Refusing symlink destination: " + str(path))
        if path.exists() and not path.is_file():
            raise ValueError("Expected a file: " + str(path))
    backup = state / "jialing/backups" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup.mkdir(parents=True, mode=0o700)
    entries = []
    for index, (path, data) in enumerate(files.items()):
        old = path.read_bytes() if path.exists() else None
        if old is not None:
            (backup / str(index)).write_bytes(old)
        entries.append(
            {
                "path": str(path),
                "old": str(index) if old is not None else None,
                "installed_sha256": digest(data),
            }
        )
    (backup / "manifest.json").write_text(json.dumps(entries, indent=2))
    completed = []
    try:
        for entry, (path, data) in zip(entries, files.items()):
            atomic_write(path, data)
            completed.append(entry)
    except OSError:
        for entry in reversed(completed):
            path = Path(entry["path"])
            if entry["old"] is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, (backup / entry["old"]).read_bytes())
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
            atomic_write(path, originals[entry["path"]])


def fontconfig_files(config):
    files = {}
    rules = config / "fontconfig/jialing.conf"
    files[rules] = (ROOT / "profile/fonts.conf").read_bytes()
    fontconfig = config / "fontconfig/fonts.conf"
    text = fontconfig.read_text() if fontconfig.exists() else "<fontconfig>\n</fontconfig>\n"
    if ET.fromstring(text).tag != "fontconfig":
        raise ValueError("Invalid fontconfig root")
    # Preserve comments, aliases, and unrelated formatting verbatim.
    text = re.sub(r"\n?<!-- Jialing begin -->.*?<!-- Jialing end -->\n?", "", text, flags=re.S)
    if "</fontconfig>" not in text:
        raise ValueError("Expected an explicit closing fontconfig element")
    include = (
        '<!-- Jialing begin -->\n<include ignore_missing="yes">'
        + escape(str(rules))
        + "</include>\n<!-- Jialing end -->\n"
    )
    files[fontconfig] = text.replace("</fontconfig>", include + "</fontconfig>").encode()
    return files


def ghostty_files(config, state):
    ghostty = config / "ghostty/config"
    text = ghostty.read_text() if ghostty.exists() else ""
    keys = {
        "font-family",
        "font-style",
        "font-size",
        "background-opacity",
        "window-padding-x",
        "window-padding-y",
    }
    lines = [line for line in text.splitlines() if line.partition("=")[0].strip() not in keys]
    include = 'config-file = ?"' + str(state / "omarchy/current/theme/ghostty.conf") + '"'
    if not any(
        "current/theme/ghostty.conf" in line and not line.lstrip().startswith("#") for line in lines
    ):
        lines.insert(0, include)
    return {ghostty: ("\n".join(lines) + "\n").encode()}


def gtk_files(config):
    files = {}
    for toolkit in ("gtk-3.0", "gtk-4.0"):
        path = config / toolkit / "settings.ini"
        ini = configparser.ConfigParser(interpolation=None)
        ini.optionxform = str
        if path.exists():
            ini.read_string(path.read_text())
        if not ini.has_section("Settings"):
            ini.add_section("Settings")
        ini.set("Settings", "gtk-font-name", "Inter 11")
        buffer = io.StringIO()
        ini.write(buffer)
        files[path] = buffer.getvalue().encode()
    return files


def profile_files(config, state):
    return fontconfig_files(config) | ghostty_files(config, state) | gtk_files(config)


def unit_quote(value):
    """Quote a systemd argument, including literal specifier/dollar characters."""
    return (
        '"'
        + str(value)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("%", "%%")
        .replace("$", "$$")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        + '"'
    )


def daylight_files(config, state, data, auto_location):
    # Use the invoking interpreter so an isolated Astral environment stays isolated.
    subprocess.run([sys.executable, "-c", "import astral"], check=True, stdout=subprocess.DEVNULL)
    script = data / "jialing/daylight.py"
    location_path = config / "omarchy/jialing-daylight.json"
    location = json.loads(location_path.read_text()) if location_path.exists() else {}
    if not isinstance(location, dict):
        raise ValueError("Daylight configuration must be a JSON object")
    if auto_location is not None:
        location["auto_location"] = auto_location
    if location.get("auto_location") is not True:
        from daylight import validate_location

        validate_location(location)
    service = (
        "[Unit]\nDescription=Jialing daylight appearance\n"
        "PartOf=graphical-session.target\nAfter=graphical-session.target\n\n"
        "[Service]\nType=oneshot\n"
    )
    for name, value in (("XDG_CONFIG_HOME", config), ("XDG_STATE_HOME", state)):
        service += "Environment=" + unit_quote(name + "=" + str(value)).replace("$$", "$") + "\n"
    service += "ExecStart=" + unit_quote(sys.executable) + " " + unit_quote(script) + "\n"
    timer = (
        "[Unit]\nDescription=Check Jialing daylight appearance every minute\n"
        "PartOf=graphical-session.target\n\n[Timer]\nOnStartupSec=20\n"
        "OnCalendar=*-*-* *:*:00\nAccuracySec=5\nPersistent=true\n"
        "Unit=jialing-daylight.service\n\n[Install]\nWantedBy=graphical-session.target\n"
    )
    return {
        script: (ROOT / "daylight.py").read_bytes(),
        location_path: (json.dumps(location, indent=2) + "\n").encode(),
        config / "systemd/user/jialing-daylight.service": service.encode(),
        config / "systemd/user/jialing-daylight.timer": timer.encode(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-apply", action="store_true", help="Write files only; no desktop commands"
    )
    parser.add_argument(
        "--daylight",
        action="store_true",
        help="Install optional scheduler files; enable timer separately",
    )
    parser.add_argument(
        "--auto-location",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Opt into hourly ipapi.co lookup (requires --daylight)",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Opt into global font and Ghostty settings",
    )
    parser.add_argument("--wallpaper", type=Path, help="Copy a local wallpaper to both variants")
    parser.add_argument("--variant", choices=("dark", "light"), default="dark")
    parser.add_argument("--restore", type=Path, help="Restore a backup, refusing subsequent edits")
    args = parser.parse_args()
    if args.auto_location is not None and not args.daylight:
        parser.error("--auto-location requires --daylight")
    if args.restore:
        restore(args.restore)
        print(json.dumps({"restored": str(args.restore)}))
        return
    config = location_root("XDG_CONFIG_HOME", ".config")
    state = location_root("XDG_STATE_HOME", ".local/state")
    files = {
        config / "omarchy/themes" / theme / name: (ROOT / "themes" / theme / name).read_bytes()
        for theme in THEMES
        for name in ASSETS
    }
    if args.wallpaper:
        if args.wallpaper.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            parser.error("--wallpaper requires a JPG, PNG, or WebP file")
        wallpaper = args.wallpaper.read_bytes()
        files.update(
            {
                config / "omarchy/themes" / theme / "backgrounds" / args.wallpaper.name: wallpaper
                for theme in THEMES
            }
        )
    if args.profile:
        files.update(profile_files(config, state))
    if args.daylight:
        files.update(
            daylight_files(
                config,
                state,
                location_root("XDG_DATA_HOME", ".local/share"),
                args.auto_location,
            )
        )
    backup = write_files(files, state)
    print(json.dumps({"backup": str(backup), "themes": list(THEMES)}), flush=True)
    if not args.no_apply:
        subprocess.run(
            [
                "omarchy",
                "theme",
                "set",
                "jialing-light" if args.variant == "light" else "jialing",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )


if __name__ == "__main__":
    try:
        main()
    except (
        OSError,
        ValueError,
        ET.ParseError,
        configparser.Error,
        subprocess.CalledProcessError,
    ) as error:
        raise SystemExit(str(error))
