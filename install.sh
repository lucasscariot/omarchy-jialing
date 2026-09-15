#!/usr/bin/env bash
# One-line entry point. Keep execution inside main so a truncated download cannot run it.
set -euo pipefail

main() {
  local option download cleanup python_cmd=python3
  local no_apply=false daylight=false restore=false explicit_variant=false
  for option in "$@"; do
    case "$option" in
      --no-apply|--help|-h) no_apply=true ;;
      --daylight) daylight=true ;;
      --restore|--restore=*) restore=true ;;
      --variant|--variant=*) explicit_variant=true ;;
    esac
  done

  command -v git >/dev/null || { echo 'Jialing needs git. Install it and retry.' >&2; return 1; }
  command -v "$python_cmd" >/dev/null || { echo 'Jialing needs Python 3.11 or newer.' >&2; return 1; }
  "$python_cmd" -c 'import sys; sys.exit(sys.version_info < (3, 11))' || {
    echo 'Jialing needs Python 3.11 or newer.' >&2; return 1;
  }
  if ! "$no_apply" && ! "$restore"; then
    command -v omarchy >/dev/null && [[ -f "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/hyprland.lua" ]] || {
      echo 'Jialing needs Omarchy with Lua Hyprland configuration (tested on 4.0.3). Use --no-apply to install files only.' >&2
      return 1
    }
  fi

  download=$(mktemp -d "${TMPDIR:-/tmp}/jialing-download.XXXXXXXX")
  printf -v cleanup 'rm -rf -- %q' "$download"
  # Capture the shell-quoted path now; the local variable is out of scope on failure.
  # shellcheck disable=SC2064
  trap "$cleanup" EXIT
  echo 'Downloading Jialing…' >&2
  git clone --quiet --depth 1 https://github.com/lucasscariot/omarchy-jialing.git "$download/source"

  # Keep the interpreter outside the temporary checkout: systemd needs it after installation.
  if "$daylight" && ! "$restore"; then
    python_cmd="${XDG_DATA_HOME:-$HOME/.local/share}/jialing-daylight/venv/bin/python"
    if [[ ! -x "$python_cmd" ]]; then
      python3 -m venv "${python_cmd%/bin/python}"
    fi
    "$python_cmd" -m pip install --quiet -r "$download/source/requirements.txt"
  fi
  if ! "$explicit_variant" && ! "$restore"; then
    local current="${XDG_STATE_HOME:-$HOME/.local/state}/omarchy/current/theme.name"
    if [[ -f "$current" ]] && [[ $(<"$current") == jialing-light ]]; then
      set -- "$@" --variant light
    fi
  fi
  "$python_cmd" "$download/source/install.py" "$@"
  if "$daylight" && ! "$no_apply" && ! "$restore"; then
    systemctl --user daemon-reload
    systemctl --user enable --now jialing-daylight.timer
    systemctl --user start jialing-daylight.service
  fi
  echo 'Jialing is ready. Keep the backup path printed above to undo this install.' >&2
  # Run cleanup while the local download variable is still in scope.
  rm -rf -- "$download"
  trap - EXIT
}

main "$@"
