"""UT-FEAT3 — Build Phase 3: spectral bands, sliding RMS unification, patching."""

from __future__ import annotations

import numpy as np
import pytest

from src.features.patching import make_patches, patch_spec
from src.features.vibration import (
    band_edges_hz,
    rms,
    sliding_rms,
    spectral_bands,
)

FS = 2000.0


# ------------------------------------------------------------------ spectral bands
def test_spectral_bands_returns_exactly_four():
    x = np.sin(2 * np.pi * 100 * np.arange(0, 1, 1 / FS))
    bands = spectral_bands(x.tolist(), FS)
    assert len(bands) == 4 and all(b >= 0 for b in bands)


def test_spectral_bands_localize_known_tones():
    t = np.arange(0, 1, 1 / FS)                      # Nyquist 1000 Hz, bands of 250 Hz
    low = np.sin(2 * np.pi * 100 * t)                # -> band 0
    high = np.sin(2 * np.pi * 800 * t)               # -> band 3
    low_bands = spectral_bands(low.tolist(), FS)
    high_bands = spectral_bands(high.tolist(), FS)
    assert np.argmax(low_bands) == 0
    assert np.argmax(high_bands) == 3
    assert low_bands[0] > 100 * max(low_bands[1:])   # energy concentrated


def test_spectral_bands_ignore_dc_offset():
    t = np.arange(0, 1, 1 / FS)
    tone = np.sin(2 * np.pi * 600 * t)               # band 2
    with_dc = tone - 1015.0                          # Bosch-style mounting offset
    assert np.argmax(spectral_bands(with_dc.tolist(), FS)) == 2


def test_spectral_bands_degenerate_inputs():
    assert spectral_bands([], FS) == [0.0] * 4
    assert spectral_bands([5.0], FS) == [0.0] * 4
    assert spectral_bands([3.0] * 100, FS) == pytest.approx([0.0] * 4, abs=1e-20)
    with pytest.raises(ValueError):
        spectral_bands([1.0, 2.0], 0.0)


def test_band_edges_cover_zero_to_nyquist():
    edges = band_edges_hz(FS, 4)
    assert edges[0][0] == 0.0 and edges[-1][1] == FS / 2
    assert all(hi - lo == pytest.approx(250.0) for lo, hi in edges)


# ------------------------------------------------------------------ sliding RMS (I-3)
def test_sliding_rms_agrees_with_one_path_rms():
    """Meta-test: the vectorized sliding RMS must equal rms() per window (I-3)."""
    rng = np.random.default_rng(42)
    x = rng.normal(0, 2, 4000)
    values, centers = sliding_rms(x, FS, window_s=0.5, hop_s=0.25)
    win, hop = int(0.5 * FS), int(0.25 * FS)
    for i, v in enumerate(values):
        seg = x[i * hop: i * hop + win]
        assert v == pytest.approx(rms(seg.tolist()), rel=1e-9)
        assert centers[i] == pytest.approx((i * hop + win // 2) / FS)


def test_sliding_rms_short_signal_is_empty():
    values, centers = sliding_rms(np.ones(10), FS, window_s=0.5, hop_s=0.25)
    assert values.size == 0 and centers.size == 0


def test_event_detector_uses_one_feature_path():
    """The ETL must not carry its own RMS implementation anymore (I-3)."""
    import inspect

    from src.etl import sensor_etl
    source = inspect.getsource(sensor_etl.EventDetector._sliding_rms)
    assert "sliding_rms(" in source and "cumsum" not in source


# ------------------------------------------------------------------ patching (D12)
def test_patch_spec_geometry_matches_d12():
    spec = patch_spec(n_samples=24_000, n_channels=3, sample_rate_hz=FS)
    assert (spec.patch_samples, spec.stride_samples) == (500, 250)
    assert spec.n_patches == 95 and spec.n_channels == 3


def test_make_patches_shape_and_content():
    window = np.arange(24_000 * 3, dtype="float64").reshape(24_000, 3)
    patches = make_patches(window, FS)
    assert patches.shape == (95, 3, 500)
    np.testing.assert_array_equal(patches[0, 0], window[:500, 0])   # first patch
    np.testing.assert_array_equal(patches[1, 2], window[250:750, 2])  # stride 250


def test_make_patches_drops_incomplete_tail():
    window = np.zeros((617, 1))                       # 617 = 500 + 117 leftover
    patches = make_patches(window, FS)
    assert patches.shape == (1, 1, 500)               # tail never padded (D10/D12)


def test_make_patches_rejects_short_window():
    with pytest.raises(ValueError):
        make_patches(np.zeros((100, 3)), FS)


def test_make_patches_deterministic():
    rng = np.random.default_rng(7)
    window = rng.normal(size=(2000, 3))
    np.testing.assert_array_equal(make_patches(window, FS), make_patches(window, FS))
