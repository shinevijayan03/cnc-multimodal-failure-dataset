"""UT-WIN — D10 window-convention module (src/tgfx/windows.py)."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.tgfx.windows import (
    INCIDENT_SPAN,
    QUERY_WINDOW,
    SUB_WINDOW_S,
    build_subwindow_frame,
    carve_subwindows,
    resolve_query_window,
    sensor_evidence_id,
    waveform_span,
)

FIXTURE_ID_PATTERN = re.compile(r"^SW_.+_\d{2}$")  # matches src/eval/fixtures.py scheme


# ------------------------------------------------------------------ carving
def test_carve_staged_span_yields_two_windows():
    # Staged corpus spans ±8 s -> starts at -8 and -5 only.
    windows = carve_subwindows("inc_x", (-8.0, 8.0))
    assert [(w.t_start, w.t_end) for w in windows] == [(-8.0, 4.0), (-5.0, 7.0)]
    assert all(abs((w.t_end - w.t_start) - SUB_WINDOW_S) < 1e-9 for w in windows)
    assert [w.window_id for w in windows] == ["SW_inc_x_00", "SW_inc_x_01"]


def test_carve_full_convention_span():
    windows = carve_subwindows("inc_x", INCIDENT_SPAN)
    # [-60, +30]: starts -60, -57, ..., +18 -> 27 windows.
    assert len(windows) == 27
    assert windows[0].t_start == -60.0
    assert windows[-1].t_end == 30.0


def test_carve_short_span_yields_none():
    assert carve_subwindows("inc_x", (-4.0, 4.0)) == []


def test_carve_clips_to_incident_bounds():
    windows = carve_subwindows("inc_x", (-100.0, 50.0))
    assert windows[0].t_start == INCIDENT_SPAN[0]
    assert windows[-1].t_end <= INCIDENT_SPAN[1]


def test_carve_rejects_bad_params():
    with pytest.raises(ValueError):
        carve_subwindows("inc_x", (-8.0, 8.0), duration_s=0.0)


# ------------------------------------------------------------------ query window
def test_query_window_full_coverage():
    q = resolve_query_window((-60.0, 30.0))
    assert (q.t_start, q.t_end) == QUERY_WINDOW
    assert q.coverage_frac == 1.0 and not q.clipped


def test_query_window_clipped_on_staged_span():
    q = resolve_query_window((-8.0, 8.0))
    assert (q.t_start, q.t_end) == (-8.0, 0.0)
    assert q.clipped and abs(q.coverage_frac - 8.0 / 12.0) < 1e-6


def test_query_window_no_overlap_is_empty_not_padded():
    q = resolve_query_window((2.0, 8.0))
    assert q.t_start == q.t_end          # empty window, no synthetic padding (D10)
    assert q.coverage_frac == 0.0 and q.clipped


# ------------------------------------------------------------------ evidence IDs
def test_sensor_evidence_id_matches_fixture_scheme():
    eid = sensor_evidence_id("inc_oracle_001", 0)
    assert eid == "SW_inc_oracle_001_00"
    assert FIXTURE_ID_PATTERN.match(eid)
    assert sensor_evidence_id("inc_oracle_001", 0) == eid  # deterministic


# ------------------------------------------------------------------ driver
def _write_waveform(path: Path, t0: float, t1: float, fs: float = 100.0) -> None:
    t_rel = np.arange(t0, t1, 1.0 / fs)
    pd.DataFrame({
        "time_s": t_rel + 1000.0, "t_rel_s": t_rel,
        "ax": 0.0, "ay": 0.0, "az": 0.0,
    }).to_parquet(path)


def test_build_subwindow_frame(tmp_path: Path):
    _write_waveform(tmp_path / "a.parquet", -8.0, 8.0)
    _write_waveform(tmp_path / "b.parquet", -4.0, 4.0)   # short span
    index = pd.DataFrame([
        {"incident_id": "inc_a", "sensor_file": "a.parquet"},
        {"incident_id": "inc_b", "sensor_file": "b.parquet"},
    ])
    frame = build_subwindow_frame(index, tmp_path)
    a = frame[frame["incident_id"] == "inc_a"]
    b = frame[frame["incident_id"] == "inc_b"]
    assert list(a["window_id"]) == ["SW_inc_a_00", "SW_inc_a_01"]
    assert not a["short_span"].any()
    # Short-span incident is recorded, not padded (D10).
    assert len(b) == 1 and b["short_span"].all() and b["window_id"].isna().all()
    assert (a["query_t_start"] == -8.0).all() and (a["query_t_end"] == 0.0).all()


def test_waveform_span_requires_t_rel():
    with pytest.raises(ValueError):
        waveform_span(pd.DataFrame({"time_s": [0.0]}))
