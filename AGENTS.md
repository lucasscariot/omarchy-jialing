# Agent instructions

This repository is the source of truth for Jialing. Make changes here first. Do not make a lasting change only in the installed copy under `~/.config/`.

For every change that affects the installed theme or hook:

1. Edit the source files in this repository.
2. Run the relevant checks (`python3 -m unittest discover -s tests -v` and `bash -n install.sh` for installer changes).
3. Apply the checkout to this computer with `python3 install.py`. The installer backs up replaced files and selects Jialing. Use `--no-apply` only when testing installation without switching the desktop theme.
4. Check the result on the live desktop, including `hyprctl configerrors` for Hyprland changes. Follow `REVIEW.md` for visual checks, and report what was verified and any test that could not run.

Keep the repository and installed configuration in sync throughout the task. If applying a change to the computer is unavailable, say so explicitly; do not present the change as live-tested.

Never edit Omarchy package files under `/usr/share/omarchy/`.
