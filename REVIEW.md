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

- 27 unittest tests pass locally with Astral 3.2, including menu-clone setup,
  repeated setup, backups, and refusal to overwrite unfamiliar menu code.
- Ruff lint and formatting checks pass.
- Theme TOML and Fontconfig XML parse successfully.
- Both variants apply on Omarchy 4.0.3-1; `hyprctl reload` succeeds and `hyprctl configerrors` is empty.
- `ghostty +validate-config` succeeds.
- Generated user service and timer pass `systemd-analyze --user verify`.
- Installed timer is active; service exits successfully and approximate location lookup returns a valid cached location.
- GitHub Actions runs the test suite on Python 3.11, 3.13, and 3.14.

## Limits

Tests do not render Quickshell or emulate a full desktop. Visual behavior relies on the supported Omarchy version and can be overridden by personal configuration. Lock styling was checked through Omarchy's preview during theme development; authentication behavior is untouched.

The frosted quick menu was checked live in both variants, including the optional
420 px width and soft shadow. That integration uses a local menu clone; it must
be reviewed against future upstream menu changes. The theme's stronger blur is
shared by other blurred desktop surfaces.

Individual file replacements are atomic. An interrupted multi-file operation is not a filesystem transaction. Restore handles file contents; activation state, caches, empty directories, and selected desktop theme are managed separately. A very small race remains between the scheduler's final theme-name check and Omarchy acquiring its theme-update lock.

IP location is approximate and may reflect a VPN endpoint. No wallpaper or font redistribution rights are implied by this repository's code license.

## One-line installer

`install.sh` bootstraps the existing installer from a temporary Git checkout. Five additional CLI tests cover argument forwarding and restore, download-failure cleanup, compatibility checks before downloading, repeat updates that preserve the light variant and personal wallpapers, and optional daylight dependency setup and service activation. GitHub downloads, dependency provisioning, and systemctl are replaced with local test doubles; the theme installer itself runs against temporary homes.

The installer also ships distinct native `preview.png` files for both variants. A regression test covers installation and restoration of an existing custom preview.

## WhiteSur default icons

Both theme variants now select a matching WhiteSur variant through `icons.theme`.
The installer provisions the pinned 2026-09-10 upstream release into versioned,
Jialing-specific user icon directories before applying the theme. It verifies the
download checksum and includes upstream licensing and source attribution. Icon
dependencies are retained when restoring theme-file backups.

The 33-test suite passes. Icon tests cover offline cache reuse, checksum failures,
relative links across light/dark variants, paths containing spaces, preservation
of existing WhiteSur installations, repeated installs, incomplete installations,
upstream installation failure, and failure while copying the staged icons.
CLI tests verify both installed theme selections resolve to installed icon sets.
Network access is mocked and CLI fixtures supply an already-installed dependency.

The real upstream installer ran locally without root. All three GTK icon caches
validate; representative folder/application icons and licensing files resolve in
both variants. Applying Jialing Light selects
`Jialing-WhiteSur-2026-09-10-light`; Hyprland reloads without config errors and
Chromium remains the default browser. Ruff checks, Python compilation, shell
syntax, and whitespace checks pass.
