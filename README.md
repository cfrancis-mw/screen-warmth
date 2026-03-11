# screen-warmth

Smoothly adjusts monitor color temperature and brightness based on time of day. Uses XRandR gamma ramps for accurate linear color scaling - the same approach as redshift/gammastep.

## Configuration

Create a `config.yaml` in the project root or at `$XDG_CONFIG_HOME/screen-warmth/config.yaml`:

```yaml
day_temp: 3500
night_temp: 2500

morning_start: 7.0
morning_end: 12.0
afternoon_start: 12.0
afternoon_end: 17.0

day_brightness: 0.90
night_brightness: 0.65

# 0.0 = no warmth, 1.0 = full blackbody
warmth_strength: 0.80

update_interval: 30

# Per-monitor overrides (optional)
monitor_overrides:
  eDP-1:
    warmth_strength: 0.55

# Explicit monitor list (auto-detected if omitted)
# monitors:
#   - eDP-1
#   - HDMI-1
```

All fields are optional and fall back to sensible defaults.

## Run

```bash
uv run screen-warmth
```

## systemd

Enable as a user service:

```bash
systemctl --user daemon-reload
systemctl --user enable --now screen-warmth.service
```

Manage:

```bash
systemctl --user status screen-warmth
systemctl --user stop screen-warmth
systemctl --user restart screen-warmth  # after config changes
journalctl --user -u screen-warmth -f   # tail logs
```
