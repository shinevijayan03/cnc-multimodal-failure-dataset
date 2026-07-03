"""Deterministic vibration feature helpers for TGFX evaluation.

This is the single import path for vibration-derived feature math. The current
implementation is intentionally small and supports the eval meta-fixtures; later
encoder and dataset tasks should extend this module instead of duplicating math.
"""

from __future__ import annotations

from math import sqrt
from statistics import fmean


def rms(values: list[float]) -> float:
    """Return root-mean-square amplitude for one numeric channel."""
    if not values:
        return 0.0
    return sqrt(fmean([value * value for value in values]))


def variance(values: list[float]) -> float:
    """Return population variance for one numeric channel."""
    if not values:
        return 0.0
    mean = fmean(values)
    return fmean([(value - mean) ** 2 for value in values])


def kurtosis(values: list[float]) -> float:
    """Return population kurtosis, or 0.0 for a zero-variance signal."""
    if not values:
        return 0.0
    mean = fmean(values)
    var = variance(values)
    if var == 0.0:
        return 0.0
    fourth = fmean([(value - mean) ** 4 for value in values])
    return fourth / (var * var)


def feature_delta(current: float, baseline: float) -> float:
    """Return relative feature change against a baseline."""
    if baseline == 0.0:
        return 0.0 if current == 0.0 else float("inf")
    return (current - baseline) / abs(baseline)


def rose(current: float, baseline: float, threshold: float = 0.20) -> bool:
    """Return true when a feature rose by at least the configured fraction."""
    return feature_delta(current, baseline) >= threshold

