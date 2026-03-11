"""CIE chromaticity / sRGB math and Kelvin-to-gamma conversion.

Uses CIE chromaticity (Kim et al.) + XYZ -> linear sRGB, which produces
physically accurate whitepoints -- the same approach as redshift/gammastep.
"""

from __future__ import annotations

from .types import Gamma

_SRGB_MATRIX = (
    (3.2404542, -1.5371385, -0.4985314),
    (-0.9692660, 1.8760108, 0.0415560),
    (0.0556434, -0.2040259, 1.0572252),
)


def _cct_to_xy(temp: float) -> tuple[float, float]:
    """Convert correlated color temperature to CIE xy chromaticity (Kim et al.)."""
    t2 = temp * temp
    t3 = t2 * temp

    if temp <= 4000:
        x = -0.2661239e9 / t3 - 0.2343589e6 / t2 + 0.8776956e3 / temp + 0.179910
    else:
        x = -3.0258469e9 / t3 + 2.1070379e6 / t2 + 0.2226347e3 / temp + 0.240390

    x2 = x * x
    x3 = x2 * x

    if temp <= 2222:
        y = -1.1063814 * x3 - 1.34811020 * x2 + 2.18555832 * x - 0.20219683
    elif temp <= 4000:
        y = -0.9549476 * x3 - 1.37418593 * x2 + 2.09137015 * x - 0.16748867
    else:
        y = 3.0817580 * x3 - 5.87338670 * x2 + 3.75112997 * x - 0.37001483

    return (x, y)


def _xy_to_srgb(x: float, y: float) -> tuple[float, float, float]:
    """Convert CIE xy chromaticity (Y=1) to linear sRGB."""
    big_x = x / y
    big_z = (1.0 - x - y) / y

    return (
        _SRGB_MATRIX[0][0] * big_x + _SRGB_MATRIX[0][1] + _SRGB_MATRIX[0][2] * big_z,
        _SRGB_MATRIX[1][0] * big_x + _SRGB_MATRIX[1][1] + _SRGB_MATRIX[1][2] * big_z,
        _SRGB_MATRIX[2][0] * big_x + _SRGB_MATRIX[2][1] + _SRGB_MATRIX[2][2] * big_z,
    )


def _normalize_rgb(r: float, g: float, b: float) -> tuple[float, float, float]:
    """Scale RGB so the brightest channel is 1.0."""
    peak = max(r, g, b)
    return (r / peak, g / peak, b / peak)


def _raw_gamma(kelvin: int) -> tuple[float, float, float]:
    """Compute normalized sRGB whitepoint for a color temperature."""
    x, y = _cct_to_xy(float(max(1667, min(25000, kelvin))))
    return _normalize_rgb(*_xy_to_srgb(x, y))


# Precompute the D65 (6500K) reference -- avoids recalculating every call.
_REF_R, _REF_G, _REF_B = _raw_gamma(6500)


def kelvin_to_gamma(kelvin: int, warmth_strength: float) -> Gamma:
    """Convert a color temperature in Kelvin to an RGB gamma multiplier.

    Normalized so that 6500K (D65 daylight) maps to Gamma(1, 1, 1).
    ``warmth_strength`` controls how much of the color-temperature shift is
    applied: 0.0 = no effect (neutral), 1.0 = full blackbody whitepoint.
    """
    r, g, b = _raw_gamma(kelvin)

    # Normalize against D65 reference
    r = min(1.0, r / _REF_R)
    g = min(1.0, g / _REF_G)
    b = min(1.0, b / _REF_B)

    # Blend toward neutral (invert so 1.0 = full warmth)
    s = 1.0 - warmth_strength
    return Gamma(
        r=r + s * (1.0 - r),
        g=g + s * (1.0 - g),
        b=b + s * (1.0 - b),
    )
