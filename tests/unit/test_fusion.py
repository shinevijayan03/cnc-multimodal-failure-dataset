"""UT-FUS — Build-A evidence selection head + multimodal context builder."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from src.graph.evidence_graph import EvidenceGraph
from src.retrieval.retriever import RetrievedEvidence
from src.fusion.select import (
    EvidenceBundle,
    build_context,
    select_evidence,
)
from src.ui.workbench import incident_bundle


def _graph() -> EvidenceGraph:
    g = EvidenceGraph()
    g.add_node("inc_a", "incident")
    for w in ("SW_inc_a_00", "SW_inc_a_01", "SW_inc_a_02"):
        g.add_node(w, "window")
    g.add_node("doc_x__c0001", "chunk")
    g.add_node("doc_x__c0002", "chunk")
    g.add_node("vid.mp4", "video")
    return g


def _incident(video: str | None = "vid.mp4") -> pd.Series:
    return pd.Series({"incident_id": "inc_a", "failure_family": "tool_wear",
                      "severity_label": "high", "regime_label": "unknown",
                      "video_file": video})


def _features() -> pd.DataFrame:
    return pd.DataFrame([
        {"window_id": "SW_inc_a_00", "t_start": -8.0, "t_end": 4.0,
         "anomaly_heuristic": 0.10, "anomaly_encoder": 0.20},
        {"window_id": "SW_inc_a_01", "t_start": -5.0, "t_end": 7.0,
         "anomaly_heuristic": 0.05, "anomaly_encoder": 0.90},
        {"window_id": "SW_inc_a_02", "t_start": -2.0, "t_end": 10.0,
         "anomaly_heuristic": 0.50, "anomaly_encoder": float("nan")},
    ])


def _tuples() -> pd.DataFrame:
    return pd.DataFrame([
        {"incident_id": "inc_a", "window_id": w, "t_start": t0, "t_end": t1,
         "alarm_state": st, "sensor_summary": f"summary {w}"}
        for w, t0, t1, st in [("SW_inc_a_00", -8.0, 4.0, "event_in_window"),
                              ("SW_inc_a_01", -5.0, 7.0, "event_in_window"),
                              ("SW_inc_a_02", -2.0, 10.0, "event_in_window")]
    ])


def _retrieved() -> list[RetrievedEvidence]:
    return [
        RetrievedEvidence("doc_x__c0001", "sop:doc_x§c0001", 0.66, 0.76, "sop",
                          "vibration", "Inspect the spindle bearing."),
        RetrievedEvidence("doc_x__c0002", "sop:doc_x§c0002", 0.60, 0.60, "sop",
                          "coolant", "Check coolant flow."),
    ]


def _summary_row() -> pd.Series:
    return pd.Series({"video_id": "vid_000", "video_file": "vid.mp4",
                      "summary": "Oscillatory shaft motion.",
                      "visual_labels": json.dumps(["chatter_marks"]),
                      "confidence": 0.95, "model": "qwen", "mode": "vlm"})


# ------------------------------------------------------------------ module-level
def test_sensor_ranking_uses_max_of_encoder_and_heuristic():
    bundle = select_evidence(_incident(), _features(), _tuples(), _retrieved(),
                             _graph(), _summary_row())
    sensor = bundle.by_modality("sensor")
    # SW_01 (enc 0.90) > SW_02 (heur 0.50, enc NaN) > SW_00 (enc 0.20)
    assert [i.evidence_id for i in sensor] == \
        ["SW_inc_a_01", "SW_inc_a_02", "SW_inc_a_00"]
    assert sensor[0].score == pytest.approx(0.90)
    assert sensor[1].score == pytest.approx(0.50)   # NaN encoder falls back
    assert sensor[0].detail == "summary SW_inc_a_01"


def test_document_and_video_items_carry_real_scores():
    bundle = select_evidence(_incident(), _features(), _tuples(), _retrieved(),
                             _graph(), _summary_row())
    docs = bundle.by_modality("document")
    assert [d.evidence_id for d in docs] == ["doc_x__c0001", "doc_x__c0002"]
    assert docs[0].score == pytest.approx(0.76)      # boosted
    assert docs[0].confidence == pytest.approx(0.66)  # raw cosine
    video = bundle.by_modality("video")
    assert video[0].confidence == pytest.approx(0.95)
    assert "VLM clip" in video[0].label


def test_selection_is_deterministic():
    a = select_evidence(_incident(), _features(), _tuples(), _retrieved(),
                        _graph(), _summary_row())
    b = select_evidence(_incident(), _features(), _tuples(), _retrieved(),
                        _graph(), _summary_row())
    assert a == b


def test_unresolvable_evidence_raises():
    bad = [RetrievedEvidence("chunk_not_in_graph", "x", 0.5, 0.5, "sop", "", "")]
    with pytest.raises(KeyError):
        select_evidence(_incident(), _features(), _tuples(), bad,
                        _graph(), _summary_row())


def test_no_video_incident_has_no_video_item():
    bundle = select_evidence(_incident(video=None), _features(), _tuples(),
                             _retrieved(), _graph(), None)
    assert bundle.by_modality("video") == []
    assert "- none" in bundle.context_text.split("DOCUMENTS")[0]


def test_missing_vlm_summary_gets_low_confidence_fallback():
    bundle = select_evidence(_incident(), _features(), _tuples(), _retrieved(),
                             _graph(), None)
    video = bundle.by_modality("video")
    assert video[0].confidence == pytest.approx(0.3)
    assert "no VLM summary" in video[0].detail


# ------------------------------------------------------------------ context builder
def test_context_contains_all_modalities_and_states():
    bundle = select_evidence(_incident(), _features(), _tuples(), _retrieved(),
                             _graph(), _summary_row())
    ctx = bundle.context_text
    assert "INCIDENT inc_a" in ctx and "failure_family=tool_wear" in ctx
    assert "SENSOR CHRONOLOGY" in ctx and "SW_inc_a_01" in ctx
    assert "sync_provenance: constructed" in ctx          # I-8 caveat
    assert "sop:doc_x§c0001" in ctx
    assert "ALARM STATES" in ctx and "event_in_window" in ctx


def test_context_builder_direct_shape():
    ctx = build_context(_incident(), [], pd.DataFrame())
    assert ctx.startswith("INCIDENT inc_a")
    assert "- none" in ctx                                # empty modalities visible


# ------------------------------------------------------------------ UI helper
def test_incident_bundle_orders_modalities_and_ranks():
    frame = pd.DataFrame([
        {"incident_id": "inc_a", "modality": "document", "rank": 1,
         "evidence_id": "d1", "score": 0.5, "confidence": 0.5, "label": "", "detail": ""},
        {"incident_id": "inc_a", "modality": "sensor", "rank": 0,
         "evidence_id": "s0", "score": 0.9, "confidence": 0.9, "label": "", "detail": ""},
        {"incident_id": "inc_a", "modality": "video", "rank": 0,
         "evidence_id": "v0", "score": 0.95, "confidence": 0.95, "label": "", "detail": ""},
        {"incident_id": "inc_b", "modality": "sensor", "rank": 0,
         "evidence_id": "x", "score": 0.1, "confidence": 0.1, "label": "", "detail": ""},
    ])
    rows = incident_bundle(frame, "inc_a")
    assert list(rows["evidence_id"]) == ["s0", "v0", "d1"]
    assert incident_bundle(frame, "inc_zz").empty


def test_bundle_serialization_round_trip():
    bundle = select_evidence(_incident(), _features(), _tuples(), _retrieved(),
                             _graph(), _summary_row())
    assert isinstance(bundle, EvidenceBundle)
    ids = bundle.ids()
    assert len(ids) == len(set(ids)) == 6                 # 3 sensor + 1 video + 2 docs
