# screen-warmth

Smoothly adjusts monitor color temperature and brightness based on time of day. Uses XRandR gamma ramps for accurate linear color scaling - the same approach as redshift/gammastep.

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
