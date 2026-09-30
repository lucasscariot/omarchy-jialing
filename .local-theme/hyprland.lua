-- Jialing: native theme appearance.

-- Indicate focus with a red-to-orange outline.
hl.config({
  animations = {
    enabled = false,
  },
  general = {
    gaps_in = 5,
    gaps_out = 10,
    border_size = 1,
    col = {
      active_border = { colors = { "rgb(ff6961)", "rgb(ff9f0a)" }, angle = 45 },
      inactive_border = "rgba(63636688)",
    },
  },
  decoration = {
    rounding = 5,
    shadow = {
      enabled = false,
    },
  },
})
