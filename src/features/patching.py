"""Patch creation — convert sensor sub-windows into PatchTST-style tokens.

A patch is a fixed-length slice of the multichannel waveform; the encoder
(Build Phase 4) consumes the resulting (n_patches, n_channels, patch_samples)
tensor. Defaults are recorded in docs/_sdd/decisions.md D12. Incomplete tail
patches are dropped (never padded), mirroring the D10 no-synthetic-data rule.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# D12 defaults: 0.25 s patches, 50% overlap. At the staged 2 kHz sample rate a
# 12 s sub-window yields 95 patches of 500 samples.
DEFAULT_PATCH_S = 0.25
DEFAULT_STRIDE_S = 0.125


@dataclass(frozen=True)
class PatchSpec:
    """Resolved patching geometry for one sub-window."""

    patch_samples: int
    stride_samples: int
    n_patches: int
    n_channels: int


def patch_spec(n_samples: int, n_channels: int, sample_rate_hz: float,
               patch_s: float = DEFAULT_PATCH_S,
               stride_s: float = DEFAULT_STRIDE_S) -> PatchSpec:
    """Compute the patch geometry; raises if the window is shorter than a patch."""
    if sample_rate_hz <= 0 or patch_s <= 0 or stride_s <= 0:
        raise ValueError("sample_rate_hz, patch_s, and stride_s must be positive")
    patch_samples = max(1, int(round(patch_s * sample_rate_hz)))
    stride_samples = max(1, int(round(stride_s * sample_rate_hz)))
    if n_samples < patch_samples:
        raise ValueError(
            f"window of {n_samples} samples is shorter than one patch "
            f"({patch_samples} samples)")
    n_patches = (n_samples - patch_samples) // stride_samples + 1
    return PatchSpec(patch_samples=patch_samples, stride_samples=stride_samples,
                     n_patches=n_patches, n_channels=n_channels)


def make_patches(window: np.ndarray, sample_rate_hz: float,
                 patch_s: float = DEFAULT_PATCH_S,
                 stride_s: float = DEFAULT_STRIDE_S) -> np.ndarray:
    """Slice a (n_samples, n_channels) window into patch tokens.

    Returns an array of shape (n_patches, n_channels, patch_samples), float64,
    deterministic for identical input. Incomplete tail samples are dropped.
    """
    window = np.asarray(window, dtype="float64")
    if window.ndim == 1:
        window = window[:, None]
    if window.ndim != 2:
        raise ValueError("window must be 1-D or 2-D (n_samples, n_channels)")
    spec = patch_spec(window.shape[0], window.shape[1], sample_rate_hz,
                      patch_s, stride_s)
    out = np.empty((spec.n_patches, spec.n_channels, spec.patch_samples))
    for i in range(spec.n_patches):
        start = i * spec.stride_samples
        out[i] = window[start:start + spec.patch_samples].T
    return out
