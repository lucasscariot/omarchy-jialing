#!/usr/bin/env bash
# One-line installer for the native Jialing theme.
set -euo pipefail

main() {
  local option download cleanup skip_apply=false
  for option in "$@"; do
    case "$option" in
      --no-apply|--help|-h|--restore|--restore=*) skip_apply=true ;;
    esac
  done

  command -v git >/dev/null || { echo 'Jialing needs git.' >&2; return 1; }
  command -v python3 >/dev/null || { echo 'Jialing needs Python 3.11 or newer.' >&2; return 1; }
  python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' || {
    echo 'Jialing needs Python 3.11 or newer.' >&2; return 1;
  }
  if ! "$skip_apply"; then
    if ! command -v omarchy >/dev/null || [[ ! -f "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/hyprland.lua" ]]; then
      echo 'Jialing needs Omarchy with Lua Hyprland configuration. Use --no-apply to install files only.' >&2
      return 1
    fi
  fi

  download=$(mktemp -d "${TMPDIR:-/tmp}/jialing-download.XXXXXXXX")
  printf -v cleanup 'rm -rf -- %q' "$download"
  # shellcheck disable=SC2064
  trap "$cleanup" EXIT
  git clone --quiet --depth 1 https://github.com/lucasscariot/omarchy-jialing.git "$download/source"
  python3 "$download/source/install.py" "$@"
  echo 'Jialing is ready. Keep the printed backup path to undo this install.' >&2
  rm -rf -- "$download"
  trap - EXIT
}

main "$@"
