"""Stand in for a previously installed WhiteSur dependency in isolated CLI tests."""

from icons import NAMES


def installed_icons(data):
    for name in NAMES:
        path = data / "icons" / name
        path.mkdir(parents=True, exist_ok=True)
        (path / "index.theme").write_text(f"[Icon Theme]\nName={name}\n")
