"""UT-WB-REAL — real pipeline artifacts (Phases 2-5) surfaced into the UI."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.ui.workbench import (
    encoder_summary,
    important_interval_events,
    incident_feature_rows,
    live_retrieval_cards,
    quality_chip,
)


def _features() -> pd.DataFrame:
    return pd.DataFrame([
        {"window_id": "SW_inc_a_00", "incident_id": "inc_a", "t_start": -8.0,
         "t_end": 4.0, "rms": 1.2, "kurtosis": 3.1, "variance": 1.5,
         "anomaly_score": 0.02, "important_start_s": -1.2, "important_end_s": -0.2,
         "spec_band_0": 1.0, "spec_band_1": 0.5, "spec_band_2": 0.2,
         "spec_band_3": 0.1},
        {"window_id": "SW_inc_a_01", "incident_id": "inc_a", "t_start": -5.0,
         "t_end": 7.0, "rms": 1.4, "kurtosis": 3.4, "variance": 1.9,
         "anomaly_score": 0.10, "important_start_s": 0.5, "important_end_s": 1.5,
         "spec_band_0": 1.1, "spec_band_1": 0.6, "spec_band_2": 0.3,
         "spec_band_3": 0.1},
    ])


def _hvib() -> pd.DataFrame:
    return pd.DataFrame([
        {"window_id": "SW_inc_a_00", "incident_id": "inc_a", "split": "val",
         "anomaly_score": 0.31},
    ])


def test_incident_feature_rows_join_encoder_scores():
    rows = incident_feature_rows(_features(), "inc_a", _hvib())
    assert len(rows) == 2
    assert rows.loc[0, "anomaly_heuristic"] == 0.02
    assert rows.loc[0, "anomaly_encoder"] == 0.31        # joined from hvib
    assert np.isnan(rows.loc[1, "anomaly_encoder"])      # window not in hvib
    assert incident_feature_rows(_features(), "inc_missing", _hvib()).empty


def test_important_interval_events_map_to_axis_and_clip():
    rows = incident_feature_rows(_features(), "inc_a")
    events = important_interval_events(rows, rel_offset=8.0, t0=0.0, t1=16.0)
    assert len(events) == 2
    assert (events[0].t_start, events[0].t_end) == (6.8, 7.8)   # -1.2..-0.2 + 8
    assert all(e.row == "SENSOR" and e.source == "derived" for e in events)
    assert "SW_inc_a_00" in events[0].label


def test_encoder_summary_states():
    rows = incident_feature_rows(_features(), "inc_a", _hvib())
    assert encoder_summary(rows, "val")["status"] == "ok"
    assert "0.310" in encoder_summary(rows, "val")["text"]
    assert encoder_summary(rows, "test")["status"] == "quarantined"
    no_scores = incident_feature_rows(_features(), "inc_a")
    assert encoder_summary(no_scores, "val")["status"] == "missing"


def test_quality_chip_states():
    labels = {"inc_a": 1, "inc_b": 0}
    assert quality_chip(labels, "inc_a", "val")["status"] == "bad"
    assert quality_chip(labels, "inc_b", "train")["status"] == "good"
    assert quality_chip(labels, "inc_a", "test")["status"] == "quarantined"
    assert quality_chip(labels, "inc_zz", "val")["status"] == "missing"


def test_live_retrieval_cards_carry_real_scores():
    hits = [{"chunk_id": "doc_x__c0007", "score": 0.6341,
             "citation": "sop:doc_x§c0007", "doc_type": "sop",
             "topic_tags": "vibration,spindle", "text": "Check the spindle."}]
    cards = live_retrieval_cards(hits, "BAAI/bge-base-en-v1.5")
    card = cards[0]
    assert card["match_pct"] == 63 and card["status"] == "Matched"
    assert card["source"] == "retrieval"                 # real, not demo
    assert "cosine 0.6341" in card["section"]
    assert card["phrases"] == ["vibration", "spindle"]
