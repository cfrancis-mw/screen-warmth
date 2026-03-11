"""Configuration loading from YAML."""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass, field, fields
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Config:
    """All tuneable parameters in one place."""

    day_temp: int = 3500
    night_temp: int = 2200

    morning_start: float = 7.0
    morning_end: float = 12.0
    afternoon_start: float = 12.0
    afternoon_end: float = 17.0

    day_brightness: float = 0.90
    night_brightness: float = 0.50

    warmth_strength: float = 0.9
    update_interval: int = 30

    monitors: tuple[str, ...] | None = None

    # Per-monitor overrides, e.g. {"eDP-1": {"warmth_strength": 0.55}}
    monitor_overrides: dict[str, dict[str, float]] = field(default_factory=dict)


_CONFIG_FIELD_NAMES = frozenset(f.name for f in fields(Config))


def load_config(path: str | Path | None = None) -> Config:
    """Load configuration from a YAML file.

    Search order:
      1. Explicit *path* argument
      2. ``$XDG_CONFIG_HOME/screen-warmth/config.yaml``
      3. ``./config.yaml``
      4. Built-in defaults (no file needed)
    """
    candidates: list[Path] = []

    if path is not None:
        candidates.append(Path(path))
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME", "")
        if xdg:
            candidates.append(Path(xdg) / "screen-warmth" / "config.yaml")
        else:
            candidates.append(Path.home() / ".config" / "screen-warmth" / "config.yaml")
        candidates.append(Path("config.yaml"))

    for candidate in candidates:
        if candidate.is_file():
            return _load_from(candidate)

    return Config()


def _load_from(path: Path) -> Config:
    """Parse a single YAML file into a Config."""
    raw = yaml.safe_load(path.read_text()) or {}

    unknown = set(raw) - _CONFIG_FIELD_NAMES
    if unknown:
        warnings.warn(
            f"Unknown config keys ignored: {', '.join(sorted(unknown))}",
            stacklevel=3,
        )

    known = {k: v for k, v in raw.items() if k in _CONFIG_FIELD_NAMES}

    # Convert monitors list to tuple
    if "monitors" in known and isinstance(known["monitors"], list):
        known["monitors"] = tuple(known["monitors"])

    # Ensure monitor_overrides values are plain dicts
    if "monitor_overrides" in known and isinstance(known["monitor_overrides"], dict):
        known["monitor_overrides"] = {
            str(k): dict(v) for k, v in known["monitor_overrides"].items()
        }

    return Config(**known)
