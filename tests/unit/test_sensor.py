"""Sensor numeric-core tests — UT-SENS-01..15."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.common.config import (
    EventDetectionCfg,
    EvidenceSpansCfg,
    FsEstimationCfg,
    SensorCfg,
    WindowingCfg,
)
from src.common.errors import ReaderError
from src.etl.sensor_etl import (
    EventDetector,
    EvidenceSpanExtractor,
    Event,
    FsEstimator,
    Normalizer,
    RawRun,
    WindowCarver,
)
from tests.conftest import make_bursts_df

SCFG = SensorCfg(datasets=[], canonical_channels=["time_s", "ax", "ay", "az"],
                 optional_channels=["ae"])


def _detect_cfg(**over):
    base = dict(channel_for_energy="az", window_s=0.5, hop_s=0.1, threshold_kind="zscore",
                threshold_value=4.0, baseline_window_s=5.0, min_event_separation_s=1.0,
                min_event_duration_s=0.1)
    base.update(over)
    return EventDetectionCfg(**base)


def _normalize(df, fs=2000.0, column_map=None):
    return Normalizer(SCFG).normalize(RawRun("r", df), column_map or {"x": "ax", "y": "ay", "z": "az"}, fs)


# --------------------------------------------------------------------------- Normalizer
def test_column_map_rename():  # UT-SENS-01
    df = pd.DataFrame({"X": [1.0, 2, 3], "Y": [4.0, 5, 6], "Z": [7.0, 8, 9]})
    out = _normalize(df, column_map={"X": "ax", "Y": "ay", "Z": "az"})
    assert list(out.columns) == ["time_s", "ax", "ay", "az"]
    assert "X" not in out.columns


def test_unmapped_columns_dropped():  # UT-SENS-02
    df = pd.DataFrame({"x": [1.0, 2], "y": [3.0, 4], "z": [5.0, 6], "junk": [9, 9]})
    out = _normalize(df)
    assert "junk" not in out.columns


def test_nonmonotonic_time_repaired():  # UT-SENS-03
    df = pd.DataFrame({"time_s": [0.0, 0.0, 0.5, 0.2, 0.9],
                       "x": [1.0] * 5, "y": [1.0] * 5, "z": [1.0] * 5})
    out = _normalize(df, fs=10.0)
    t = out["time_s"].to_numpy()
    assert np.all(np.diff(t) > 0)
    np.testing.assert_allclose(t, np.arange(5) / 10.0)


# --------------------------------------------------------------------------- FsEstimator
def test_median_dt_recovers_fs():  # UT-SENS-04
    df = pd.DataFrame({"time_s": np.arange(1000) / 2000.0, "az": np.zeros(1000)})
    fs = FsEstimator(FsEstimationCfg(method="median_dt")).estimate(df, {})
    assert abs(fs - 2000.0) / 2000.0 < 0.01


def test_implausible_fs_rejected():  # UT-SENS-05
    df = pd.DataFrame({"time_s": np.arange(100) / 5.0, "az": np.zeros(100)})  # 5 Hz
    with pytest.raises(ReaderError):
        FsEstimator(FsEstimationCfg(method="median_dt", min_plausible_hz=100)).estimate(df, {})


def test_fixed_fs_honored():  # UT-SENS-06
    fs = FsEstimator(FsEstimationCfg(method="fixed")).estimate(pd.DataFrame({"az": [0.0]}),
                                                               {}, fs_hz=1000.0)
    assert fs == 1000.0


# --------------------------------------------------------------------------- EventDetector
def test_detect_k_bursts():  # UT-SENS-07
    df = _normalize(make_bursts_df(dur=20.0, burst_times=(5, 10, 15)))
    cfg = _detect_cfg()
    events = EventDetector(cfg).detect(df, 2000.0, cfg)
    assert len(events) == 3
    for ev, t in zip(sorted(events, key=lambda e: e.t_event_s), (5, 10, 15)):
        assert abs(ev.t_event_s - t) < 1.0


def test_no_false_positive_on_noise():  # UT-SENS-08
    df = _normalize(make_bursts_df(dur=20.0, burst_times=(), seed=3))
    cfg = _detect_cfg(threshold_value=6.0)
    assert EventDetector(cfg).detect(df, 2000.0, cfg) == []


def test_merge_close_events():  # UT-SENS-09
    df = _normalize(make_bursts_df(dur=20.0, burst_times=(5.0, 5.5)))
    cfg = _detect_cfg(min_event_separation_s=2.0)
    assert len(EventDetector(cfg).detect(df, 2000.0, cfg)) == 1


def test_drop_short_blip():  # UT-SENS-10
    df = _normalize(make_bursts_df(dur=20.0, burst_times=(10.0,)))
    cfg = _detect_cfg(min_event_duration_s=5.0)   # the smeared burst run is < 5 s
    assert EventDetector(cfg).detect(df, 2000.0, cfg) == []


def test_threshold_monotonicity():  # UT-SENS-11
    df = _normalize(make_bursts_df(dur=30.0, burst_times=(5, 12, 20, 27)))
    low = len(EventDetector(_detect_cfg(threshold_value=3.0)).detect(
        df, 2000.0, _detect_cfg(threshold_value=3.0)))
    high = len(EventDetector(_detect_cfg(threshold_value=6.0)).detect(
        df, 2000.0, _detect_cfg(threshold_value=6.0)))
    assert high <= low


def test_segment_center_event_mode():  # UT-SENS-16
    df = _normalize(make_bursts_df(dur=20.0, burst_times=(10.0,)), fs=2000.0)
    events = EventDetector(_detect_cfg(method="segment_center")).detect(df, 2000.0)
    assert len(events) == 1
    assert events[0].t_event_s == pytest.approx(10.0, abs=0.01)


# --------------------------------------------------------------------------- Window / spans
def _long_signal(fs=200.0, dur=200.0, t_burst=100.0):
    n = int(fs * dur)
    rng = np.random.default_rng(0)
    z = rng.normal(0, 1.0, n)
    i = int(t_burst * fs)
    z[i:i + int(0.6 * fs)] += rng.normal(0, 12.0, int(0.6 * fs))
    df = pd.DataFrame({"x": rng.normal(0, 1, n), "y": rng.normal(0, 1, n), "z": z - 1015.0})
    return Normalizer(SCFG).normalize(RawRun("r", df), {"x": "ax", "y": "ay", "z": "az"}, fs)


def test_window_length_and_zeroing():  # UT-SENS-12
    fs = 200.0
    df = _long_signal(fs=fs, t_burst=100.0)
    ev = Event(t_event_s=100.0, t_start_s=99.7, t_end_s=100.3, score=10.0)
    win = WindowCarver().carve(df, ev, fs, WindowingCfg(pre_event_s=60.0, post_event_s=30.0))
    assert win is not None
    assert abs((win.window_end_s - win.window_start_s) - 90.0) < 0.1
    assert abs(win.n_samples - 90 * fs) < 5
    assert abs(win.df["t_rel_s"].min() + 60.0) < 0.1
    assert abs(win.df["t_rel_s"].max() - 30.0) < 0.1
    assert abs(win.df["t_rel_s"].abs().min()) < 0.05         # ~0 at event


def test_drop_partial_window():  # UT-SENS-13
    df = _long_signal(t_burst=5.0)
    ev = Event(t_event_s=5.0, t_start_s=4.7, t_end_s=5.3, score=10.0)
    assert WindowCarver().carve(df, ev, 200.0,
                                WindowingCfg(pre_event_s=60.0, post_event_s=30.0,
                                             drop_partial_windows=True)) is None


def test_keep_partial_when_allowed():  # UT-SENS-14
    df = _long_signal(t_burst=5.0)
    ev = Event(t_event_s=5.0, t_start_s=4.7, t_end_s=5.3, score=10.0)
    win = WindowCarver().carve(df, ev, 200.0,
                               WindowingCfg(pre_event_s=60.0, post_event_s=30.0,
                                            drop_partial_windows=False))
    assert win is not None and win.n_samples > 0


def test_evidence_spans_cover_crossing():  # UT-SENS-15
    fs = 200.0
    df = _long_signal(fs=fs, t_burst=100.0)
    ev = Event(t_event_s=100.0, t_start_s=99.7, t_end_s=100.3, score=10.0)
    win = WindowCarver().carve(df, ev, fs, WindowingCfg(pre_event_s=60.0, post_event_s=30.0))
    cfg = EvidenceSpansCfg(pad_s=0.5, max_spans=5)
    spans = EvidenceSpanExtractor(cfg).extract(win, ev, cfg)
    assert 1 <= len(spans) <= cfg.max_spans
    s = spans[0]
    assert s.start_s <= -0.3 + 0.01 and s.end_s >= 0.3 - 0.01   # covers crossing (rel time)
    assert s.start_s >= win.df["t_rel_s"].min() - 1e-6
