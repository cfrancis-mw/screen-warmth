"""Time-based interpolation between day and night values."""

from __future__ import annotations

from .config import Config


def _schedule_lerp(hour: float, day_val: float, night_val: float, cfg: Config) -> float:
    """Interpolate between day and night values based on hour of day.

    Schedule:
      afternoon_end  - morning_start  -> night value
      morning_start  - morning_end    -> ramp night -> day
      afternoon_start - afternoon_end -> ramp day -> night
    """
    if hour < cfg.morning_start or hour >= cfg.afternoon_end:
        return night_val

    if hour < cfg.morning_end:
        progress = (hour - cfg.morning_start) / (cfg.morning_end - cfg.morning_start)
        return night_val + progress * (day_val - night_val)

    if hour < cfg.afternoon_end:
        progress = (hour - cfg.afternoon_start) / (
            cfg.afternoon_end - cfg.afternoon_start
        )
        return day_val + progress * (night_val - day_val)

    return night_val


def scheduled_temperature(hour: float, cfg: Config) -> int:
    """Return the target color temperature for the given hour."""
    return int(_schedule_lerp(hour, cfg.day_temp, cfg.night_temp, cfg))


def scheduled_brightness(hour: float, cfg: Config) -> float:
    """Return the target brightness (0.0-1.0) for the given hour."""
    return round(_schedule_lerp(hour, cfg.day_brightness, cfg.night_brightness, cfg), 3)
