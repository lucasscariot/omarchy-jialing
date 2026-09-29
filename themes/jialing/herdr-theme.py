#!/usr/bin/env python3
"""Sync Jialing's Herdr colors with the selected Omarchy theme."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import tomllib


START = "# >>> Jialing theme\n"
END = "# <<< Jialing theme\n"
PREVIOUS = "# Jialing previous: "
SECTION = re.compile(r"(?m)(?=^\[{1,2}[^\]\n]+\]{1,2}[ \t]*(?:#.*)?$)")
BLOCK = re.compile(r"(?ms)^# >>> Jialing theme\n(.*?)^# <<< Jialing theme\n")


def split_sections(text):
    return [part for part in SECTION.split(text) if part]


def section_name(section):
    match = re.match(r"^\[([^]\n]+)\]", section)
    return match.group(1) if match else None


def clear_managed(section):
    match = BLOCK.search(section)
    if not match:
        return section, False
    created = "# Jialing created section" in match.group(1)
    clean = section[:match.start()] + section[match.end():]
    clean = re.sub(r"(?m)^# Jialing previous: (.*)$", r"\1", clean)
    if created and not clean.partition("\n")[2].strip():
        return "", True
    return clean, True


def set_managed(section, values, created):
    lines = section.splitlines(keepends=True)
    kept = []
    for line in lines:
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        if match and match.group(1) in values:
            kept.append(PREVIOUS + line)
        else:
            kept.append(line)
    block = START
    if created:
        block += "# Jialing created section\n"
    block += "".join(f'{key} = "{value}"\n' if isinstance(value, str) else f"{key} = {str(value).lower()}\n" for key, value in values.items())
    block += END
    body = "".join(kept)
    trailing_newlines = max(1, len(body) - len(body.rstrip("\n")))
    return body.rstrip("\n") + "\n" + block + "\n" * (trailing_newlines - 1)


def merge(original, palette=None):
    sections = split_sections(original)
    wanted = palette or {}
    result = []
    for section in sections:
        name = section_name(section)
        if name not in ("theme", "theme.custom"):
            result.append(section)
            continue
        section, _ = clear_managed(section)
        if not section:
            continue
        if name in wanted:
            section = set_managed(section, wanted[name], created=False)
        result.append(section)
    if palette:
        existing = {section_name(section) for section in result}
        for name, values in wanted.items():
            if name not in existing:
                result.append(set_managed(f"[{name}]\n", values, created=True))
    updated = "".join(result)
    tomllib.loads(updated)
    return updated


def main():
    config = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    state = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
    selected = (state / "omarchy/current/theme.name").read_text().strip()
    path = config / "herdr/config.toml"
    if not path.exists():
        return
    if path.is_symlink() or not path.is_file():
        raise ValueError("Herdr config must be a regular file")
    source = config / "omarchy/themes/jialing/herdr.toml"
    palette = None
    if selected == "jialing":
        data = tomllib.loads(source.read_text())
        palette = {"theme": {"name": data["theme"]["name"], "auto_switch": data["theme"]["auto_switch"]},
                   "theme.custom": data["theme"]["custom"]}
    original = path.read_text()
    updated = merge(original, palette)
    if updated == original:
        return
    backup = path.with_name("config.toml.before-jialing-theme")
    if not backup.exists():
        shutil.copy2(path, backup)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(updated)
    try:
        temporary.chmod(path.stat().st_mode & 0o777)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    if shutil.which("herdr"):
        subprocess.run(["herdr", "server", "reload-config"], capture_output=True, timeout=5, check=False)


if __name__ == "__main__":
    main()
