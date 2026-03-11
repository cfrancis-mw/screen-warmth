"""Shared data types."""

from __future__ import annotations

from typing import NamedTuple


class Gamma(NamedTuple):
    """RGB gamma multipliers (each 0.0-1.0)."""

    r: float
    g: float
    b: float

    def __str__(self) -> str:
        return f"{self.r:.3f}:{self.g:.3f}:{self.b:.3f}"
