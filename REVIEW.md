# Review notes

## Scope

Reviewed native theme assets, optional font profile, installer/update/restore, and the daylight scheduler. Tests target the two agreed user-facing boundaries: installation and daylight behavior.

## Corrections

- Install both variants and preserve additional files and wallpapers.
- Make the global font profile explicit; preserve unrelated font aliases and terminal shortcuts.
- Keep byte-for-byte backups in private directories and print their location before applying desktop changes.
- Preflight destinations and refuse symlinks before writing any files.
- Refuse restores after subsequent edits or incomplete backups before changing any destinations.
- Validate location shapes, coordinate ranges, and timezones; tolerate corrupt cache content.
- Cache location lookups hourly, including failures; retain a valid cached city or configured fallback.
- Leave themes outside the Jialing pair alone, including a manual selection during a slow location lookup.
- Separate file installation from timer activation; document how to stop and restore the scheduler.
- Use the invoking Python environment in the generated service and quote paths for systemd.
- Remove personal location settings, wallpaper binaries, bar layouts, and plugin snapshots from publication scope.

## Validation

- 18 unittest tests pass locally with Astral 3.2.
- Ruff lint and formatting checks pass.
- Theme TOML and Fontconfig XML parse successfully.
- Both variants apply on Omarchy 4.0.3-1; `hyprctl reload` succeeds and `hyprctl configerrors` is empty.
- `ghostty +validate-config` succeeds.
- Generated user service and timer pass `systemd-analyze --user verify`.
- Installed timer is active; service exits successfully and approximate location lookup returns a valid cached location.
- GitHub Actions runs the test suite on Python 3.11, 3.13, and 3.14.

## Limits

Tests do not render Quickshell or emulate a full desktop. Visual behavior relies on the supported Omarchy version and can be overridden by personal configuration. Lock styling was checked through Omarchy's preview during theme development; authentication behavior is untouched.

Individual file replacements are atomic. An interrupted multi-file operation is not a filesystem transaction. Restore handles file contents; activation state, caches, empty directories, and selected desktop theme are managed separately. A very small race remains between the scheduler's final theme-name check and Omarchy acquiring its theme-update lock.

IP location is approximate and may reflect a VPN endpoint. No wallpaper or font redistribution rights are implied by this repository's code license.
