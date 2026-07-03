"""UT-WB — incident workbench logic (src/ui/workbench.py, v2 reference UI)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from src.ui.workbench import (
    DEMO_DURATION_S,
    DEMO_INCIDENT_ID,
    TIMELINE_ROWS,
    PlaybackState,
    active_events,
    build_ai_explanation,
    build_claim_rows,
    build_sop_cards,
    build_timeline_events,
    demo_incident,
    demo_sensor_frame,
    demo_timeline_events,
    events_frame,
    export_report_json,
    incident_axis,
    live_readouts,
    rolling_rms_frame,
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


T0, T1 = 0.0, 16.0
REL = 8.0          # t_rel −8..+8 mapped onto the 0..16 display axis


# ------------------------------------------------------------------ axis
def test_incident_axis_is_zero_based():
    df = pd.DataFrame({"t_rel_s": np.linspace(-8.0, 8.0, 100), "ax": 0.0})
    t0, t1, rel_offset = incident_axis(df)
    assert (t0, t1) == (0.0, 16.0)
    assert rel_offset == 8.0            # axis_time = t_rel + 8


# ------------------------------------------------------------------ timeline
def test_timeline_renders_all_required_rows(incident):
    events = build_timeline_events(incident, T0, T1, rel_offset=REL)
    assert {e.row for e in events} == set(TIMELINE_ROWS)


def test_event_bars_have_labels_spans_colors_and_provenance(incident):
    events = build_timeline_events(incident, T0, T1, rel_offset=REL)
    for e in events:
        assert e.label and e.t_start < e.t_end and e.color.startswith("#")
        assert T0 <= e.t_start and e.t_end <= T1
        assert e.source in {"incident", "derived", "demo", "user"}
    # Real sensor span (-2..1.5 rel) lands at 6..9.5 on the display axis.
    real = [e for e in events if e.source == "incident"]
    assert any(e.t_start == 6.0 and e.t_end == 9.5 for e in real)
    frame = events_frame(events, current_time_s=7.0)
    demo_labels = frame[frame["source"] == "demo"]["display_label"]
    assert (demo_labels.str.contains("demo")).all()


def test_sensor_baseline_is_complement_of_evidence(incident):
    events = sensor_events(incident, T0, T1, rel_offset=REL)
    baseline = [e for e in events if e.source == "derived"]
    assert baseline and all(not (e.t_start < 7.0 < e.t_end) for e in baseline)


def test_user_snapshot_notes_land_on_notes_row(incident):
    notes = [{"t": 5.0, "label": "Snapshot @ 5s"}]
    events = build_timeline_events(incident, T0, T1, rel_offset=REL, user_notes=notes)
    user = [e for e in events if e.source == "user"]
    assert len(user) == 1 and user[0].row == "NOTES"
    assert user[0].contains(5.0) and user[0].label == "Snapshot @ 5s"


# ------------------------------------------------------------------ playback
def test_play_through_advances_current_time():
    state = PlaybackState(t0=T0, t1=T1, current_time_s=T0)
    state.play()
    state.tick(2.0)
    assert state.current_time_s == pytest.approx(2.0)
    state.playback_rate = 2.0
    state.tick(1.0)
    assert state.current_time_s == pytest.approx(4.0)


def test_stop_pauses_playback():
    state = PlaybackState(t0=T0, t1=T1, current_time_s=3.0, is_playing=True)
    state.stop()
    state.tick(5.0)
    assert state.current_time_s == 3.0 and not state.is_playing


def test_playback_stops_at_end_and_replays_from_start():
    state = PlaybackState(t0=T0, t1=T1, current_time_s=T1 - 0.5, is_playing=True)
    state.tick(10.0)
    assert state.current_time_s == T1 and not state.is_playing
    state.play()
    assert state.current_time_s == T0 and state.is_playing


def test_seek_and_step_clamp_to_axis():
    state = PlaybackState(t0=T0, t1=T1)
    state.seek(999.0)
    assert state.current_time_s == T1
    state.step(5.0)
    assert state.current_time_s == T1
    state.seek(-999.0)
    assert state.current_time_s == T0
    state.step(-1.0)
    assert state.current_time_s == T0


# ------------------------------------------------------------------ sync
def test_video_offset_tracks_shared_time_proportionally():
    state = PlaybackState(t0=T0, t1=T1, current_time_s=8.0)   # halfway
    assert video_offset_for(state, clip_duration_s=8.0) == pytest.approx(4.0)
    state.seek(T1)
    assert video_offset_for(state, clip_duration_s=8.0) == pytest.approx(8.0)
    assert video_offset_for(PlaybackState(), 8.0) == 0.0


def test_cursor_active_flags_in_events_frame(incident):
    events = build_timeline_events(incident, T0, T1, rel_offset=REL)
    frame = events_frame(events, current_time_s=7.0)
    active_ids = set(frame[frame["active"]]["event_id"])
    assert active_ids == {e.event_id for e in active_events(events, 7.0)}
    assert any(i.startswith("ev_sensor") for i in active_ids)


# ------------------------------------------------------------------ sensor display (I-3 path)
def _waveform(n_seconds: float = 4.0, fs: float = 200.0) -> pd.DataFrame:
    t_rel = np.arange(-n_seconds / 2, n_seconds / 2, 1.0 / fs)
    rng = np.random.default_rng(7)
    burst = np.where(t_rel > 0, 5.0, 1.0)
    return pd.DataFrame({
        "t_rel_s": t_rel,
        "ax": rng.normal(0, 1, len(t_rel)),
        "ay": rng.normal(0, 1, len(t_rel)),
        "az": rng.normal(0, burst) - 1000.0,   # DC offset like the real corpus
    })


def test_rolling_rms_frame_channels_and_axis():
    frame = rolling_rms_frame(_waveform(), rel_offset=2.0)
    assert set(frame["channel"]) == {"ax RMS", "ay RMS", "az RMS", "Vib RMS"}
    assert frame["t"].min() >= 0.0 and frame["t"].max() <= 4.0
    # az RMS after the burst must exceed the pre-burst level (DC removed).
    az = frame[frame["channel"] == "az RMS"]
    early = az[az["t"] < 1.5]["value"].mean()
    late = az[az["t"] > 2.5]["value"].mean()
    assert late > 2 * early


def test_live_readouts_flag_anomaly_after_burst():
    frame = rolling_rms_frame(_waveform(), rel_offset=2.0)
    az_late = [r for r in live_readouts(frame, t=3.5) if r["channel"] == "az RMS"]
    az_early = [r for r in live_readouts(frame, t=0.5) if r["channel"] == "az RMS"]
    assert az_late[0]["anomaly"] is True
    assert az_early[0]["anomaly"] is False


# ------------------------------------------------------------------ DEMO incident
def test_demo_incident_matches_reference_scenario():
    inc = demo_incident()
    assert str(inc["incident_id"]) == DEMO_INCIDENT_ID
    frame = demo_sensor_frame()
    assert set(frame["channel"]) == {"Vib RMS", "HF Energy", "Pressure Var",
                                     "Temp Delta", "Motor Current"}
    assert frame["t"].max() <= DEMO_DURATION_S
    events = build_timeline_events(inc, 0.0, DEMO_DURATION_S)
    by_label = {e.label: e for e in events}
    assert (by_label["Vib Anomaly"].t_start, by_label["Vib Anomaly"].t_end) == (18.0, 27.0)
    assert (by_label["Shaft Wobble"].t_start, by_label["Shaft Wobble"].t_end) == (18.0, 24.0)
    assert (by_label["SOP 4.2 Matched"].t_start, by_label["SOP 4.2 Matched"].t_end) == (18.0, 27.0)
    assert {e.row for e in events} == set(TIMELINE_ROWS)
    assert all(e.source == "demo" for e in demo_timeline_events())


def test_demo_sensor_frame_is_deterministic():
    a = demo_sensor_frame()
    b = demo_sensor_frame()
    pd.testing.assert_frame_equal(a, b)


# ------------------------------------------------------------------ SOP cards
def test_sop_cards_use_real_chunk_ids_and_tag_phrases(incident):
    chunks = pd.DataFrame([{
        "chunk_id": "doc_a__c0001", "doc_type": "sop", "n_tokens": 40,
        "text": "Check for chatter and tool wear on the spindle before restart.",
        "topic_tags": json.dumps(["tool_wear", "vibration"]),
    }])
    cards = build_sop_cards(incident, chunks, pd.DataFrame())
    assert len(cards) == 1
    card = cards[0]
    assert card["ref"] == "SOP doc_a__c0001"
    assert "tool wear" in card["phrases"]         # real tag found in real text
    assert 70 <= card["match_pct"] <= 95 and card["source"] == "demo"


def test_demo_sop_cards_match_reference():
    cards = build_sop_cards(demo_incident(), pd.DataFrame(), pd.DataFrame())
    refs = {c["ref"]: c for c in cards}
    assert refs["SOP 4.2"]["match_pct"] == 94 and refs["SOP 4.2"]["status"] == "Matched"
    assert refs["SOP 5.7.3"]["status"] == "Partially Matched"


# ------------------------------------------------------------------ export
def test_export_report_contains_metadata_events_and_claims(incident):
    events = build_timeline_events(incident, T0, T1, rel_offset=REL)
    explanation = build_ai_explanation(incident, events)
    claims = build_claim_rows(events)
    cards = build_sop_cards(incident, pd.DataFrame(), pd.DataFrame())
    state = PlaybackState(t0=T0, t1=T1, current_time_s=7.0)
    payload = json.loads(export_report_json(incident, events, explanation, claims,
                                            state, cards))
    assert payload["incident"]["incident_id"] == "inc_demo_001"
    assert payload["time_axis"] == {"t0": T0, "t1": T1, "cursor_at_export": 7.0}
    assert len(payload["timeline_events"]) == len(events)
    assert payload["ai_explanation"] and payload["claim_verification"]
    assert "demo" in payload["provenance_note"]


# ------------------------------------------------------------------ evidence panel
def test_ai_explanation_grounded_in_real_span(incident):
    events = build_timeline_events(incident, T0, T1, rel_offset=REL)
    sentences = build_ai_explanation(incident, events)
    grounded = [s for s in sentences if s["source"] == "incident"]
    assert grounded and "t=6s" in grounded[0]["text"]
    assert grounded[0]["evidence"]


def test_claim_rows_mark_unverified_demo_claims(incident):
    events = build_timeline_events(incident, T0, T1, rel_offset=REL)
    rows = build_claim_rows(events)
    statuses = {r["status"] for r in rows}
    assert any("UNVERIFIED" in s for s in statuses)
    assert any("SUPPORTED" in s for s in statuses)
