"""Degree-based trigonometry used by azulene's drawing coordinates."""

from __future__ import annotations

import math as _math
from collections.abc import Sequence
from typing import SupportsFloat


def sin(angle: SupportsFloat) -> float:
    """Return the sine of *angle*, where *angle* is expressed in degrees."""

    return _math.sin(_math.radians(float(angle)))


def cos(angle: SupportsFloat) -> float:
    """Return the cosine of *angle*, where *angle* is expressed in degrees."""

    return _math.cos(_math.radians(float(angle)))


def tan(angle: SupportsFloat) -> float:
    """Return the tangent of *angle*, where *angle* is expressed in degrees."""

    return _math.tan(_math.radians(float(angle)))


def blend_color(
    color1: Sequence[SupportsFloat],
    color2: Sequence[SupportsFloat],
    alpha: SupportsFloat,
) -> list[float]:
    """Mix two three-channel colours and return a three-item list.

    ``alpha`` is the weight of ``color2``; ``1 - alpha`` is the weight of
    ``color1``.  Channel values are not clamped, so drawing code can retain
    values outside 0..255 until final rasterization.
    """

    if (
        isinstance(color1, (str, bytes))
        or not isinstance(color1, Sequence)
        or len(color1) != 3
    ):
        raise ValueError("color1 must be a three-item sequence")
    if (
        isinstance(color2, (str, bytes))
        or not isinstance(color2, Sequence)
        or len(color2) != 3
    ):
        raise ValueError("color2 must be a three-item sequence")
    try:
        amount = float(alpha)
        first = [float(channel) for channel in color1]
        second = [float(channel) for channel in color2]
    except (TypeError, ValueError) as error:
        raise TypeError("colour channels and alpha must be numbers") from error
    if not _math.isfinite(amount) or not 0.0 <= amount <= 1.0:
        raise ValueError("alpha must be a finite number between 0 and 1")
    if not all(_math.isfinite(channel) for channel in first + second):
        raise ValueError("colour channels must be finite")
    inverse = 1.0 - amount
    return [
        first[index] * inverse + second[index] * amount
        for index in range(3)
    ]


pi = _math.pi

__all__ = ["sin", "cos", "tan", "blend_color", "pi"]

