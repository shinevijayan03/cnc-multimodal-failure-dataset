"""UT-SF3 — Build Phase 3 sensor-feature producer (src/tgfx/sensor_features.py)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.tgfx.sensor_features import (
    anomaly_score,
    build_window_row,
    important_interval,
    validate_contract_sample,
    window_sha256,
    window_signal,
)

FS = 2000.0


def _waveform(burst_at: float | None = None, t0: float = -8.0, t1: float = 8.0,
              seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t_rel = np.arange(t0, t1, 1.0 / FS)
    az = rng.normal(0, 1, len(t_rel)) - 1015.0        # DC mounting offset
    if burst_at is not None:
        mask = (t_rel >= burst_at) & (t_rel < burst_at + 0.6)
        az[mask] += rng.normal(0, 12, mask.sum())
    return pd.DataFrame({
        "time_s": t_rel + 1000.0, "t_rel_s": t_rel,
        "ax": rng.normal(0, 1, len(t_rel)),
        "ay": rng.normal(0, 1, len(t_rel)),
        "az": az,
    })


def test_window_signal_removes_dc_offset_and_slices_exact_count():
    _sliced, signal = window_signal(_waveform(), -8.0, 4.0, FS)
    assert abs(float(np.median(signal))) < 1.0        # ~zero after median removal
    assert len(signal) == int(12.0 * FS)              # exact despite float noise


def test_build_window_row_contract_fields_and_burst_response():
    wf = _waveform(burst_at=-1.0)
    quiet = build_window_row("inc_t", "SW_inc_t_00", -8.0, 4.0, FS, _waveform(),
                             baseline_rms=None, sensor_file="f.parquet")
    burst = build_window_row("inc_t", "SW_inc_t_00", -8.0, 4.0, FS, wf,
                             baseline_rms=quiet["rms"], sensor_file="f.parquet")
    assert burst["rms"] > quiet["rms"]
    assert burst["anomaly_score"] > 0.0
    assert burst["n_patches"] == 95 and burst["patch_samples"] == 500
    bands = [burst[f"spec_band_{i}"] for i in range(4)]
    assert len(bands) == 4 and all(b >= 0 for b in bands)
    # Important interval (peak-RMS 1 s window) must overlap the burst at -1.0..-0.4
    # and stay inside the sub-window.
    assert -8.0 <= burst["important_start_s"] < -0.4
    assert -1.0 < burst["important_end_s"] <= 4.0


def test_window_sha256_is_stable_and_content_sensitive():
    wf = _waveform()
    sliced, _ = window_signal(wf, -8.0, 4.0, FS)
    assert window_sha256(sliced) == window_sha256(sliced)
    other, _ = window_signal(_waveform(seed=9), -8.0, 4.0, FS)
    assert window_sha256(sliced) != window_sha256(other)


def test_anomaly_score_bounds():
    assert anomaly_score(1.0, 1.0) == 0.0             # no rise
    assert anomaly_score(0.5, 1.0) == 0.0             # below baseline
    assert 0.0 < anomaly_score(1.3, 1.0) < anomaly_score(3.0, 1.0) < 1.0
    assert anomaly_score(1.0, 0.0) == 1.0             # infinite relative rise


def test_important_interval_degenerate_signal():
    lo, hi = important_interval(np.zeros(5), FS, -8.0, 4.0)
    assert (lo, hi) == (-8.0, 4.0)                    # falls back to full window


def test_contract_validation_sample_passes():
    wf = _waveform(burst_at=0.5)
    row = build_window_row("inc_t", "SW_inc_t_00", -8.0, 4.0, FS, wf,
                           baseline_rms=None, sensor_file="f.parquet")
    validated = validate_contract_sample([row], {"inc_t": wf}, n=1)
    assert validated == 1                             # pydantic SensorWindow accepted


def test_contract_validation_rejects_bad_duration():
    wf = _waveform()
    row = build_window_row("inc_t", "SW_inc_t_00", -8.0, 4.0, FS, wf,
                           baseline_rms=None, sensor_file="f.parquet")
    row = {**row, "t_end": row["t_start"] + 11.0}     # not 12.0 s
    with pytest.raises(Exception):
        validate_contract_sample([row], {"inc_t": wf}, n=1)
