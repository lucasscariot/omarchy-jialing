-- Jialing: window chrome. Lantern light on graphite.
--
-- The focused window carries a red-to-amber outline and a faint warm glow
-- (Hyprland renders a shadow colour far stronger than its alpha suggests, so
-- keep this alpha tiny); other windows sit behind a neutral hairline and a
-- soft neutral shadow.
-- Corners are squircles. Windows open, close, and move instantly, but borders
-- and layers cross-fade so focus changes and popups feel settled, not abrupt.

local active_border = { colors = { "rgba(f0705fff)", "rgba(f2a74eff)" }, angle = 45 }
local inactive_border = "rgba(3a3a4099)"

hl.config({
  general = {
    gaps_in = 6,
    gaps_out = 12,
    border_size = 2,
    col = {
      active_border = active_border,
      inactive_border = inactive_border,
    },
  },

  group = {
    col = {
      border_active = active_border,
      border_inactive = inactive_border,
    },
    groupbar = {
      height = 22,
      indicator_height = 2,
      gradients = false,
      text_color = "rgb(f2f2f6)",
      text_color_inactive = "rgba(d8d8de99)",
      col = {
        active = "rgba(f2a74e2e)",
        inactive = "rgba(ffffff0c)",
      },
    },
  },

  decoration = {
    rounding = 10,
    rounding_power = 3,
    shadow = {
      enabled = true,
      range = 18,
      render_power = 3,
      offset = "0 4",
      color = "rgba(f2a74e08)",
      color_inactive = "rgba(00000050)",
    },
    blur = {
      enabled = false,
    },
    dim_inactive = false,
  },

  animations = {
    enabled = true,
  },
})

-- Motion: instant windows, soft light.
hl.curve("jialingOut", { type = "bezier", points = { { 0.2, 0.8 }, { 0.2, 1 } } })
hl.animation({ leaf = "global", enabled = true, speed = 10, bezier = "default" })
hl.animation({ leaf = "windows", enabled = false })
hl.animation({ leaf = "fade", enabled = true, speed = 1.4, bezier = "jialingOut" })
hl.animation({ leaf = "fadeIn", enabled = true, speed = 1.4, bezier = "jialingOut" })
hl.animation({ leaf = "fadeOut", enabled = true, speed = 1.2, bezier = "jialingOut" })
hl.animation({ leaf = "fadeSwitch", enabled = false })
hl.animation({ leaf = "border", enabled = true, speed = 3, bezier = "jialingOut" })
hl.animation({ leaf = "borderangle", enabled = false })
hl.animation({ leaf = "layers", enabled = true, speed = 1.6, bezier = "jialingOut", style = "fade" })
hl.animation({ leaf = "layersIn", enabled = true, speed = 1.6, bezier = "jialingOut", style = "fade" })
hl.animation({ leaf = "layersOut", enabled = true, speed = 1.2, bezier = "jialingOut", style = "fade" })
hl.animation({ leaf = "workspaces", enabled = false })
