"""Deterministic vibration feature helpers — the ONE feature path (I-3).

This is the single import path for vibration-derived feature math: RMS,
sliding RMS, 4-band spectral energy, kurtosis, variance, and feature deltas.
The encoder, verifier, gold-label generator, ETL event detector, and UI all
import these functions; duplicating this math anywhere violates the TGFX
constitution (CLAUDE.md I-3).
"""

from __future__ import annotations

from math import sqrt
from statistics import fmean

import numpy as np


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


def sliding_rms(x: "np.ndarray", fs: float, window_s: float,
                hop_s: float) -> tuple["np.ndarray", "np.ndarray"]:
    """Sliding-window RMS over a 1-D signal; returns (rms, window_center_times_s).

    Moved verbatim from the sensor ETL event detector (Build Phase 3) so the
    only sliding-RMS implementation lives on the one feature path. The cumsum
    formulation is numerically equivalent to applying :func:`rms` per window
    (asserted by the eval meta-tests).
    """
    win = max(1, int(round(window_s * fs)))
    hop = max(1, int(round(hop_s * fs)))
    x = np.asarray(x, dtype="float64")
    if x.size < win:
        return np.empty(0), np.empty(0)
    csum = np.concatenate([[0.0], np.cumsum(x ** 2)])
    starts = np.arange(0, x.size - win + 1, hop)
    out = np.sqrt((csum[starts + win] - csum[starts]) / win)
    centers = (starts + win // 2) / fs
    return out, centers


def band_edges_hz(sample_rate_hz: float, n_bands: int = 4) -> list[tuple[float, float]]:
    """Equal-width frequency band edges from 0 Hz to Nyquist."""
    if sample_rate_hz <= 0 or n_bands <= 0:
        raise ValueError("sample_rate_hz and n_bands must be positive")
    nyquist = sample_rate_hz / 2.0
    width = nyquist / n_bands
    return [(i * width, (i + 1) * width) for i in range(n_bands)]


def spectral_bands(values: list[float], sample_rate_hz: float,
                   n_bands: int = 4) -> list[float]:
    """Mean spectral power in *n_bands* equal-width bands up to Nyquist.

    The signal is detrended (mean removed) so the DC mounting offset does not
    dominate band 0. Returns exactly *n_bands* non-negative floats — the
    ``SensorWindow.spectral_energy`` contract field uses n_bands=4.
    A constant or empty signal yields all-zero bands.
    """
    if sample_rate_hz <= 0 or n_bands <= 0:
        raise ValueError("sample_rate_hz and n_bands must be positive")
    x = np.asarray(values, dtype="float64")
    if x.size < 2:
        return [0.0] * n_bands
    x = x - x.mean()
    power = np.abs(np.fft.rfft(x)) ** 2 / x.size
    freqs = np.fft.rfftfreq(x.size, d=1.0 / sample_rate_hz)
    bands: list[float] = []
    for lo, hi in band_edges_hz(sample_rate_hz, n_bands):
        mask = (freqs >= lo) & (freqs < hi) if hi < sample_rate_hz / 2.0 \
            else (freqs >= lo) & (freqs <= hi)
        bands.append(float(power[mask].mean()) if mask.any() else 0.0)
    return bands

