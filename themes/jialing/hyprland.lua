-- Jialing: native theme appearance.

-- Indicate focus with opacity instead of a border.
hl.config({
  animations = {
    enabled = false,
  },
  general = {
    gaps_in = 5,
    gaps_out = 10,
    border_size = 0,
    col = { active_border = "#0A84FF", inactive_border = "#636366" },
  },
  decoration = {
    rounding = 8,
    active_opacity = 1.0,
    inactive_opacity = 0.85,
    shadow = {
      enabled = true,
      range = 12,
      render_power = 3,
      color = "rgba(00000055)",
    },
    blur = {
      enabled = true,
      size = 10,
      passes = 3,
      ignore_opacity = true,
    },
  },
})

-- Frost the shell cards and bar flyouts, excluding transparent overlay areas.
hl.layer_rule({
  match = { namespace = "^(omarchy-bar|omarchy-keyboard-panel|omarchy-notifications|omarchy-osd|omarchy-menu|omarchy-clipboard|omarchy-emojis|omarchy-reminders|lucasscariot-notification-center)$" },
  blur = true,
  blur_popups = true,
  ignore_alpha = 0.2,
})
