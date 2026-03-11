"""Monitor control via XRandR gamma ramps (libXrandr + libX11).

Sets the gamma look-up table directly through XRRSetCrtcGamma so that
color-temperature and brightness are applied as *linear* multipliers on
each channel — the same approach redshift/gammastep use.  The xrandr CLI's
``--gamma`` flag is an *exponent* (power curve), which is why we bypass it.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import subprocess
from ctypes import POINTER, Structure, c_int, c_ulong, c_ushort

from .types import Gamma

# ---------------------------------------------------------------------------
# Xlib / XRandR ctypes bindings
# ---------------------------------------------------------------------------

_xlib = ctypes.cdll.LoadLibrary(ctypes.util.find_library("X11") or "libX11.so.6")
_xrr = ctypes.cdll.LoadLibrary(
    ctypes.util.find_library("Xrandr") or "libXrandr.so.2"
)


class _XRRCrtcGamma(Structure):
    _fields_ = [
        ("size", c_int),
        ("red", POINTER(c_ushort)),
        ("green", POINTER(c_ushort)),
        ("blue", POINTER(c_ushort)),
    ]


class _XRRScreenResources(Structure):
    _fields_ = [
        ("timestamp", c_ulong),
        ("configTimestamp", c_ulong),
        ("ncrtc", c_int),
        ("crtcs", POINTER(c_ulong)),
        ("noutput", c_int),
        ("outputs", POINTER(c_ulong)),
        ("nmode", c_int),
        ("modes", ctypes.c_void_p),
    ]


class _XRROutputInfo(Structure):
    _fields_ = [
        ("timestamp", c_ulong),
        ("crtc", c_ulong),
        ("name", ctypes.c_char_p),
        ("nameLen", c_int),
        ("mm_width", c_ulong),
        ("mm_height", c_ulong),
        ("connection", c_ushort),
        ("subpixel_order", c_ushort),
        ("ncrtc", c_int),
        ("crtcs", POINTER(c_ulong)),
        ("nclone", c_int),
        ("clones", POINTER(c_ulong)),
        ("nmode", c_int),
        ("npreferred", c_int),
        ("modes", POINTER(c_ulong)),
    ]


# Xlib
_xlib.XOpenDisplay.restype = c_ulong
_xlib.XOpenDisplay.argtypes = [ctypes.c_char_p]
_xlib.XDefaultRootWindow.restype = c_ulong
_xlib.XDefaultRootWindow.argtypes = [c_ulong]
_xlib.XFlush.argtypes = [c_ulong]
_xlib.XCloseDisplay.argtypes = [c_ulong]

# XRandR — screen resources
_xrr.XRRGetScreenResourcesCurrent.restype = POINTER(_XRRScreenResources)
_xrr.XRRGetScreenResourcesCurrent.argtypes = [c_ulong, c_ulong]
_xrr.XRRFreeScreenResources.argtypes = [POINTER(_XRRScreenResources)]
_xrr.XRRFreeScreenResources.restype = None

# XRandR — output info
_xrr.XRRGetOutputInfo.restype = POINTER(_XRROutputInfo)
_xrr.XRRGetOutputInfo.argtypes = [
    c_ulong,
    POINTER(_XRRScreenResources),
    c_ulong,
]
_xrr.XRRFreeOutputInfo.argtypes = [POINTER(_XRROutputInfo)]
_xrr.XRRFreeOutputInfo.restype = None

# XRandR — gamma
_xrr.XRRGetCrtcGammaSize.restype = c_int
_xrr.XRRGetCrtcGammaSize.argtypes = [c_ulong, c_ulong]
_xrr.XRRAllocGamma.restype = POINTER(_XRRCrtcGamma)
_xrr.XRRAllocGamma.argtypes = [c_int]
_xrr.XRRSetCrtcGamma.restype = None
_xrr.XRRSetCrtcGamma.argtypes = [c_ulong, c_ulong, POINTER(_XRRCrtcGamma)]
_xrr.XRRFreeGamma.restype = None
_xrr.XRRFreeGamma.argtypes = [POINTER(_XRRCrtcGamma)]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_crtcs(dpy: int, names: list[str]) -> dict[str, int]:
    """Map output names to their active CRTC XIDs via XRandR."""
    root = _xlib.XDefaultRootWindow(dpy)
    res = _xrr.XRRGetScreenResourcesCurrent(dpy, root)
    if not res:
        return {}

    target = set(names)
    result: dict[str, int] = {}

    for i in range(res.contents.noutput):
        output_id = res.contents.outputs[i]
        info = _xrr.XRRGetOutputInfo(dpy, res, output_id)
        if not info:
            continue
        name = info.contents.name.decode()
        crtc = info.contents.crtc
        _xrr.XRRFreeOutputInfo(info)

        if name in target and crtc:
            result[name] = crtc

    _xrr.XRRFreeScreenResources(res)
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class Display:
    """Wraps XRandR gamma-ramp control for a set of monitors."""

    def __init__(self, monitors: tuple[str, ...] | list[str] | None = None) -> None:
        if monitors:
            self._monitors = list(monitors)
        else:
            self._monitors = self._detect()
        if not self._monitors:
            raise RuntimeError("No monitors detected")

        self._dpy = _xlib.XOpenDisplay(None)
        if not self._dpy:
            raise RuntimeError("Cannot open X display")

        self._crtcs = _resolve_crtcs(self._dpy, self._monitors)
        if not self._crtcs:
            raise RuntimeError(
                f"No active CRTCs found for monitors: {', '.join(self._monitors)}"
            )

    @property
    def monitors(self) -> list[str]:
        """Return a copy of the monitor list."""
        return list(self._monitors)

    @staticmethod
    def _detect() -> list[str]:
        """Auto-detect connected monitor names from xrandr."""
        result = subprocess.run(
            ["xrandr", "--listmonitors"],
            capture_output=True,
            text=True,
        )
        return [
            line.split()[-1]
            for line in result.stdout.splitlines()
            if line.strip() and not line.strip().startswith("Monitors:")
        ]

    def apply(self, gamma: Gamma, brightness: float) -> None:
        """Set the same gamma ramp on all monitors."""
        for name in self._crtcs:
            self.apply_to(name, gamma, brightness)
        _xlib.XFlush(self._dpy)

    def apply_to(self, name: str, gamma: Gamma, brightness: float) -> None:
        """Set the gamma ramp for a single monitor (does not flush)."""
        crtc = self._crtcs.get(name)
        if crtc is None:
            return
        size = _xrr.XRRGetCrtcGammaSize(self._dpy, crtc)
        if size < 2:
            return

        ramp = _xrr.XRRAllocGamma(size)
        scale = 65535.0 / (size - 1)
        r_mul = gamma.r * brightness
        g_mul = gamma.g * brightness
        b_mul = gamma.b * brightness
        for i in range(size):
            base = i * scale
            ramp.contents.red[i] = min(int(base * r_mul + 0.5), 65535)
            ramp.contents.green[i] = min(int(base * g_mul + 0.5), 65535)
            ramp.contents.blue[i] = min(int(base * b_mul + 0.5), 65535)

        _xrr.XRRSetCrtcGamma(self._dpy, crtc, ramp)
        _xrr.XRRFreeGamma(ramp)

    def flush(self) -> None:
        """Flush pending X requests."""
        _xlib.XFlush(self._dpy)

    def reset(self) -> None:
        """Reset all monitors to neutral gamma and full brightness."""
        self.apply(Gamma(1.0, 1.0, 1.0), 1.0)
