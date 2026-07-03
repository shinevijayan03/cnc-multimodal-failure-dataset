"""UT-WB — incident workbench logic (src/ui/workbench.py)."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from src.ui.workbench import (
    TIMELINE_ROWS,
    PlaybackState,
    active_events,
    build_ai_explanation,
    build_claim_rows,
    build_timeline_events,
    events_frame,
    export_report_json,
    sensor_events,
    video_offset_for,
)


@pytest.fixture
def incident() -> pd.Series:
    return pd.Series({
        "incident_id": "inc_demo_001",
        "machine_family": "cnc_mill",
        "source_dataset": "demo",
        "failure_family": "tool_wear",
        "severity_label": "high",
        "split": "val",
        "window_start_s": 100.0,
        "window_end_s": 116.0,
        "sensor_file": "data_processed/sensor_windows/inc_demo_001.parquet",
        "video_file": "data_processed/video/vid_000.mp4",
        "sensor_relevant_spans": json.dumps([{"start_s": -2.0, "end_s": 1.5}]),
        "video_relevant_spans": json.dumps([]),
        "sop_chunk_ids": json.dumps(["doc_a__c0001", "doc_a__c0002"]),
        "maintenance_chunk_ids": json.dumps(["doc_b__c0003"]),
    })


T0, T1 = -8.0, 8.0


# ------------------------------------------------------------------ timeline (tests 1, 2)
def test_timeline_renders_all_required_rows(incident):
    events = build_timeline_events(incident, T0, T1)
    assert {e.row for e in events} == set(TIMELINE_ROWS)


def test_event_bars_have_labels_spans_and_provenance(incident):
    events = build_timeline_events(incident, T0, T1)
    for e in events:
        assert e.label and e.t_start < e.t_end
        assert T0 <= e.t_start and e.t_end <= T1
        assert e.source in {"incident", "derived", "demo"}
    # The real sensor evidence span is carried through verbatim.
    real = [e for e in events if e.source == "incident"]
    assert any(e.t_start == -2.0 and e.t_end == 1.5 for e in real)
    # Demo bars are explicitly marked in the display label.
    frame = events_frame(events, current_time_s=0.0)
    demo_labels = frame[frame["source"] == "demo"]["display_label"]
    assert (demo_labels.str.contains("demo")).all()


def test_sensor_baseline_is_complement_of_evidence(incident):
    events = sensor_events(incident, T0, T1)
    baseline = [e for e in events if e.source == "derived"]
    assert baseline and all(not (e.t_start < 0 < e.t_end) for e in baseline)


# ------------------------------------------------------------------ playback (tests 3-5)
def test_play_through_advances_current_time():
    state = PlaybackState(t0=T0, t1=T1, current_time_s=T0)
    state.play()
    state.tick(2.0)
    assert state.current_time_s == pytest.approx(T0 + 2.0)
    state.playback_rate = 2.0
    state.tick(1.0)
    assert state.current_time_s == pytest.approx(T0 + 4.0)


def test_stop_pauses_playback():
    state = PlaybackState(t0=T0, t1=T1, current_time_s=0.0, is_playing=True)
    state.stop()
    before = state.current_time_s
    state.tick(5.0)                      # tick while stopped must not move time
    assert state.current_time_s == before and not state.is_playing


def test_playback_stops_at_end_and_replays_from_start():
    state = PlaybackState(t0=T0, t1=T1, current_time_s=T1 - 0.5, is_playing=True)
    state.tick(10.0)
    assert state.current_time_s == T1 and not state.is_playing
    state.play()                          # play at the end restarts
    assert state.current_time_s == T0 and state.is_playing


def test_seek_clamps_to_axis():
    state = PlaybackState(t0=T0, t1=T1)
    state.seek(999.0)
    assert state.current_time_s == T1
    state.seek(-999.0)
    assert state.current_time_s == T0


# ------------------------------------------------------------------ sync (tests 6-7)
def test_video_offset_tracks_shared_time_proportionally():
    state = PlaybackState(t0=T0, t1=T1, current_time_s=0.0)   # halfway through axis
    assert video_offset_for(state, clip_duration_s=8.0) == pytest.approx(4.0)
    state.seek(T1)
    assert video_offset_for(state, clip_duration_s=8.0) == pytest.approx(8.0)
    assert video_offset_for(PlaybackState(), 8.0) == 0.0      # degenerate axis safe


def test_cursor_active_flags_in_events_frame(incident):
    events = build_timeline_events(incident, T0, T1)
    frame = events_frame(events, current_time_s=0.0)
    active_ids = set(frame[frame["active"]]["event_id"])
    assert active_ids == {e.event_id for e in active_events(events, 0.0)}
    assert active_ids                                          # cursor hits something
    # The real evidence span (-2.0..1.5) must be active at t=0.
    assert any(i.startswith("ev_sensor") for i in active_ids)


# ------------------------------------------------------------------ export (test 8)
def test_export_report_contains_metadata_events_and_claims(incident):
    events = build_timeline_events(incident, T0, T1)
    explanation = build_ai_explanation(incident, events)
    claims = build_claim_rows(events)
    state = PlaybackState(t0=T0, t1=T1, current_time_s=1.0)
    payload = json.loads(export_report_json(incident, events, explanation, claims, state))
    assert payload["incident"]["incident_id"] == "inc_demo_001"
    assert payload["incident"]["failure_family"] == "tool_wear"
    assert payload["time_axis"] == {"t0": T0, "t1": T1, "cursor_at_export": 1.0}
    assert len(payload["timeline_events"]) == len(events)
    assert payload["ai_explanation"] and payload["claim_verification"]
    assert "demo" in payload["provenance_note"]


# ------------------------------------------------------------------ evidence panel
def test_ai_explanation_grounded_in_real_span(incident):
    events = build_timeline_events(incident, T0, T1)
    sentences = build_ai_explanation(incident, events)
    grounded = [s for s in sentences if s["source"] == "incident"]
    assert grounded and "t=-2.0s" in grounded[0]["text"]
    assert grounded[0]["evidence"]                    # every claim cites evidence ids


def test_claim_rows_mark_unverified_demo_claims(incident):
    events = build_timeline_events(incident, T0, T1)
    rows = build_claim_rows(events)
    assert rows
    statuses = {r["status"] for r in rows}
    assert any("UNVERIFIED" in s for s in statuses)
    assert any("SUPPORTED" in s for s in statuses)    # span-anchored claim
