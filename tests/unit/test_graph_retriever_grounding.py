"""UT-P6 — evidence graph, runtime retriever, temporal grounding (Phase 6)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from src.graph.evidence_graph import EvidenceGraph
from src.retrieval.retriever import (
    IncidentRetriever,
    RetrievedEvidence,
    sensor_summary_text,
)
from src.temporal.grounding import build_aligned_tuples
from src.ui.workbench import grounded_explanation, grounded_sop_events


# ------------------------------------------------------------------ graph
def _graph() -> EvidenceGraph:
    g = EvidenceGraph()
    g.add_node("inc_a", "incident", split="val")
    g.add_node("SW_inc_a_00", "window", t_start=-8.0, t_end=4.0)
    g.add_node("SW_inc_a_01", "window", t_start=-5.0, t_end=7.0)
    g.add_node("doc_x__c0007", "chunk", doc_type="sop", topic_tags="vibration")
    g.add_node("doc_x", "doc")
    g.add_node("vid.mp4", "video")
    g.add_edge("inc_a", "SW_inc_a_00", "has_window")
    g.add_edge("doc_x__c0007", "doc_x", "part_of")
    g.add_edge("inc_a", "vid.mp4", "video_matched", sync_provenance="constructed")
    return g


def test_graph_resolve_returns_node_and_edges():
    g = _graph()
    node = g.resolve("SW_inc_a_00")
    assert node["kind"] == "window" and node["t_start"] == -8.0
    assert {"from": "inc_a", "rel": "has_window"} in node["in"]
    video = g.resolve("inc_a")
    assert any(e["rel"] == "video_matched" and e["sync_provenance"] == "constructed"
               for e in video["out"])


def test_graph_unresolvable_raises_and_resolves_predicate():
    g = _graph()
    assert g.resolves("doc_x__c0007") and not g.resolves("SW_nope_00")
    with pytest.raises(KeyError):
        g.resolve("SW_nope_00")
    with pytest.raises(KeyError):
        g.add_edge("inc_a", "missing_node", "rel")


def test_graph_round_trip(tmp_path):
    g = _graph()
    path = tmp_path / "graph.json"
    g.save(path)
    loaded = EvidenceGraph.load(path)
    assert len(loaded) == len(g) and loaded.n_edges == g.n_edges
    assert loaded.resolve("inc_a")["split"] == "val"


# ------------------------------------------------------------------ retriever
def _features() -> pd.DataFrame:
    return pd.DataFrame([
        {"window_id": "SW_inc_a_00", "t_start": -8.0, "t_end": 4.0, "rms": 100.0,
         "kurtosis": 3.0, "variance": 1.0, "anomaly_heuristic": 0.0,
         "important_start_s": -1.0, "important_end_s": 0.0,
         "anomaly_encoder": 0.2},
        {"window_id": "SW_inc_a_01", "t_start": -5.0, "t_end": 7.0, "rms": 130.0,
         "kurtosis": 4.5, "variance": 1.4, "anomaly_heuristic": 0.2,
         "important_start_s": 0.5, "important_end_s": 1.5,
         "anomaly_encoder": 0.6},
    ])


def test_sensor_summary_text_is_real_and_directional():
    text = sensor_summary_text(_features())
    assert "rose" in text and "100 to 130" in text and "kurtosis up to 4.5" in text


class _StubStore:
    embedder_name = "hashing_fallback"

    def require_embedder(self, name):
        assert name == self.embedder_name

    def search(self, _vec, k, where=None):
        return [
            {"chunk_id": "c_plain", "score": 0.70, "citation": "sop:d§c1",
             "doc_type": "sop", "topic_tags": "coolant", "text": "t1"},
            {"chunk_id": "c_topical", "score": 0.68, "citation": "sop:d§c2",
             "doc_type": "sop", "topic_tags": "vibration,tool_wear", "text": "t2"},
        ][:k]


class _StubEmbedder:
    name = "hashing_fallback"

    def embed(self, texts, queries=False):
        return np.zeros((len(texts), 4), dtype="float32")


def test_retriever_topic_boost_reranks():
    retriever = IncidentRetriever(_StubStore(), _StubEmbedder(),
                                  {"tool_wear": ["vibration", "tool_wear"]})
    incident = pd.Series({"incident_id": "inc_a", "failure_family": "tool_wear"})
    hits = retriever.retrieve(incident, _features(), k=2)
    # c_topical (0.68 + 2*0.05 boost) must outrank c_plain (0.70).
    assert [h.evidence_id for h in hits] == ["c_topical", "c_plain"]
    assert hits[0].boosted_score == pytest.approx(0.78)
    assert isinstance(hits[0], RetrievedEvidence)


# ------------------------------------------------------------------ grounding
def test_build_aligned_tuples_contract_chronology_and_resolution():
    graph = _graph()
    incident = pd.Series({"incident_id": "inc_a", "failure_family": "tool_wear",
                          "regime_label": "unknown", "video_file": "vid.mp4"})
    retrieved = [RetrievedEvidence("doc_x__c0007", "sop:doc_x§c0007", 0.7, 0.8,
                                   "sop", "vibration", "Inspect the bearing.")]
    tuples = build_aligned_tuples(incident, _features(), retrieved, graph)
    assert len(tuples) == 2                              # pydantic accepted both
    assert tuples[0].alarm_state == "event_in_window"    # -8..4 contains t=0
    assert tuples[0].timestamp_span == (-8.0, 4.0)
    assert "RMS 100.0" in tuples[0].sensor_summary
    assert "encoder anomaly 0.200" in tuples[0].sensor_summary
    assert "constructed" in tuples[0].clip_summary       # I-8 caveat travels
    assert set(tuples[0].evidence_ids) == {"SW_inc_a_00", "doc_x__c0007", "vid.mp4"}


def test_build_aligned_tuples_rejects_unresolvable_evidence():
    graph = _graph()
    incident = pd.Series({"incident_id": "inc_a", "failure_family": "tool_wear",
                          "regime_label": "unknown", "video_file": None})
    bad = [RetrievedEvidence("chunk_not_in_graph", "x", 0.5, 0.5, "sop", "", "")]
    with pytest.raises(KeyError):
        build_aligned_tuples(incident, _features(), bad, graph)


def test_grounded_ui_helpers_consume_tuple_frame():
    frame = pd.DataFrame([{
        "incident_id": "inc_a", "window_id": "SW_inc_a_00",
        "t_start": -8.0, "t_end": 4.0, "alarm_state": "event_in_window",
        "sensor_summary": "RMS 100.0, kurtosis 3.00, peak interval -1.0s to 0.0s, "
                          "heuristic anomaly 0.000",
        "retrieved_citation": "sop:doc_x§c0007", "retrieved_score": 0.70,
        "evidence_ids": json.dumps(["SW_inc_a_00", "doc_x__c0007"]),
    }])
    events = grounded_sop_events(frame, rel_offset=8.0, t0=0.0, t1=16.0)
    assert len(events) == 1
    assert events[0].source == "grounded" and events[0].row == "SOP"
    assert (events[0].t_start, events[0].t_end) == (0.0, 12.0)
    sentences = grounded_explanation(frame)
    assert sentences[0]["evidence"] == ["SW_inc_a_00"]
    assert sentences[0]["source"] == "incident"
