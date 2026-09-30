# Review

Run `python3 -m unittest discover -s tests -v` and `bash -n install.sh`. The tests install into temporary directories and cover both install and restore; they do not change the live desktop.

On an Omarchy 4 desktop, check the standard installation with `omarchy theme install`: the palette, preview, opaque shell panels, and generated Ghostty colors should apply. Omarchy's default border width, corners, and animations remain in this mode.

For the local installer, check the 1 px red/orange outline following the focused window and the subtle neutral outline on unfocused windows. Both should have 5 px circular corners; inspect the highlighted lower corners at the display's normal scale for a continuous curve without a dark notch. Also check no shadows or blur, shell panels, menu, and Ghostty colors. If Herdr is installed, check its darker sidebar, subtle dividers, and selected rows. Switch to another theme and back to confirm the Herdr override follows Jialing. Check `hyprctl configerrors` after applying Jialing.
