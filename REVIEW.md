# Review

Run `python3 -m unittest discover -s tests -v` and `bash -n install.sh`. The tests install into temporary directories and cover both install and restore; they do not change the live desktop.

On an Omarchy 4 desktop, install Jialing and check the theme selector preview, shell panels, menu, square windows, window opacity, and Ghostty colors. If Herdr is installed, check its darker sidebar, subtle dividers, and selected rows. Switch to another theme and back to confirm the Herdr override follows Jialing. Check `hyprctl configerrors` after applying Jialing.
