"""Entry point for screen-warmth daemon."""

from __future__ import annotations

import signal
import sys
import time
from datetime import datetime

from .color import kelvin_to_gamma
from .config import Config, load_config
from .display import Display
from .schedule import scheduled_brightness, scheduled_temperature


def main(cfg: Config | None = None) -> None:
    cfg = cfg or load_config()
    display = Display(monitors=cfg.monitors)
    monitors = display.monitors

    print(f"screen-warmth: managing {', '.join(monitors)}")
    print(f"  Temp:   {cfg.day_temp}K day / {cfg.night_temp}K night")
    print(f"  Bright: {cfg.day_brightness:.0%} day / {cfg.night_brightness:.0%} night")
    print(f"  Warm -> Cool: {cfg.morning_start:.1f}h - {cfg.morning_end:.1f}h")
    print(f"  Cool -> Warm: {cfg.afternoon_start:.1f}h - {cfg.afternoon_end:.1f}h")

    def on_exit(_signum: int, _frame: object) -> None:
        print("\nscreen-warmth: resetting display and exiting.")
        display.reset()
        sys.exit(0)

    signal.signal(signal.SIGINT, on_exit)
    signal.signal(signal.SIGTERM, on_exit)

    last_state: tuple[int, float] | None = None

    while True:
        now = datetime.now()
        hour = now.hour + now.minute / 60.0

        temp = scheduled_temperature(hour, cfg)
        brightness = scheduled_brightness(hour, cfg)
        state = (temp, brightness)

        if state != last_state:
            for name in monitors:
                overrides = cfg.monitor_overrides.get(name, {})
                strength = overrides.get("warmth_strength", cfg.warmth_strength)
                gamma = kelvin_to_gamma(temp, strength)
                display.apply_to(name, gamma, brightness)
            display.flush()
            gamma = kelvin_to_gamma(temp, cfg.warmth_strength)
            print(f"  [{now:%H:%M:%S}] {temp}K {brightness:.0%}  (gamma {gamma})")
            last_state = state

        time.sleep(cfg.update_interval)


if __name__ == "__main__":
    main()
