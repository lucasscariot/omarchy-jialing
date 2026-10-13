# Review

Run `python3 -m unittest discover -s tests -v` and `bash -n install.sh`. The tests install into temporary directories and cover install, restore, the Herdr hook, palette contrast, and the agreement of the focus gradient across `colors.toml`, `shell.toml`, `hyprland.lua`, and `herdr.toml`; they do not change the live desktop.

On an Omarchy 4 desktop, check the standard installation with `omarchy theme install`: the palette, preview, wallpaper, Yaru-yellow icons, shell surfaces, and generated Ghostty colors should apply. Omarchy's default border width, corners, shadows, and animations remain in this mode.

For the local installer, check:

- The focused window has a 2 px red-to-amber outline with a faint warm haze just outside it; unfocused windows have a neutral hairline and a soft dark shadow. Corners are 10 px squircles; inspect the lower corners at the display's normal scale for a continuous curve.
- Opening, closing, and moving windows is instant; focus changes and popups cross-fade briefly.
- A notification (`omarchy-notification-send Jialing "Lantern light"`) shows a raised card with a gradient hairline and a thicker amber edge on the left, and an amber countdown.
- The quick menu (`omarchy menu`) and launcher show a raised card with a white hairline; the chosen row is a flat tile with amber text and no outline.
- The lock screen field (`quickshell ipc -p /usr/share/omarchy/shell call lock preview`) is borderless, with the same edge on all four sides; a wrong password shows a red message.
- Ghostty uses the softened palette: amber-tinted selection, steel-blue ANSI blue.
- If Herdr is installed, its sidebar is darker, section headers and the active tab are amber, and alerts are red. Switch to another theme and back to confirm the Herdr override follows Jialing.

Check `hyprctl configerrors` after applying Jialing.
