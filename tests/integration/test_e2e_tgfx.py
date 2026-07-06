"""E2E-TGFX — full backend chain over a synthetic workspace (Phases 2-6).

Runs the real stage implementations end-to-end on the temp `workspace`
fixture: ETL -> incident assembly -> D10 sub-windows -> Phase 3 features ->
vector index (hashing fallback) -> evidence graph -> temporal grounding ->
UI helpers. Asserts contract validity, 100% evidence-id resolution (I-2),
chronology, and that the UI consumes the grounded output.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.etl.assemble_incidents import IncidentAssembler
from src.etl.sensor_etl import SensorETL
from src.etl.text_etl import TextETL
from src.graph.evidence_graph import build_graph, graph_path
from src.retrieval.build_index import build_index
from src.temporal import grounding as grounding_mod
from src.tgfx.sensor_features import build_sensor_features
from src.tgfx.windows import build_subwindow_index
from src.ui.workbench import (
    grounded_explanation,
    grounded_sop_events,
    incident_feature_rows,
    incident_tuples,
)


@pytest.fixture
def grounded_workspace(tmp_path, monkeypatch):
    """Run the whole backend chain; suppress run-record appends in tests.

    Uses the conftest workspace recipe but with ±8 s incident windows so the
    D10 12-second sub-windows fit (the default mini workspace uses ±3/±2 s
    windows, which correctly yield zero sub-windows — short-span behavior).
    """
    from src.common.config import load_config
    from tests.conftest import MINI_YAML, TINY_MANUAL_MD, make_bursts_df

    yaml_text = MINI_YAML.replace(
        "windowing: { pre_event_s: 3.0, post_event_s: 2.0, drop_partial_windows: true }",
        "windowing: { pre_event_s: 8.0, post_event_s: 8.0, drop_partial_windows: false }")
    (tmp_path / "config").mkdir()
    (tmp_path / "data_raw" / "demo").mkdir(parents=True)
    (tmp_path / "data_raw" / "text_manuals").mkdir(parents=True)
    make_bursts_df().to_csv(tmp_path / "data_raw" / "demo" / "run1.csv", index=False)
    (tmp_path / "data_raw" / "text_manuals" / "tiny_manual.md").write_text(
        TINY_MANUAL_MD, encoding="utf-8")
    (tmp_path / "config" / "dataset.yaml").write_text(yaml_text, encoding="utf-8")
    cfg = load_config(tmp_path / "config" / "dataset.yaml")

    monkeypatch.setattr(grounding_mod, "append_run_record", lambda *_a, **_k: None)
    SensorETL(cfg).run()
    TextETL(cfg).run()
    IncidentAssembler(cfg).run()
    windows = build_subwindow_index(cfg)
    features = build_sensor_features(cfg, validate_n=2)
    index = build_index(cfg, kind="hashing")
    graph = build_graph(cfg)
    graph.save(graph_path(cfg))
    summary = grounding_mod.ground_corpus(cfg, write=True)
    return cfg, {"windows": windows, "features": features,
                 "index": index, "graph": graph, "grounding": summary}


def test_e2e_chain_produces_grounded_tuples(grounded_workspace):
    cfg, results = grounded_workspace
    # Every stage produced output.
    assert results["windows"]["subwindows"] > 0
    assert results["features"]["windows"] == results["windows"]["subwindows"]
    assert results["features"]["contract_validated"] >= 1
    assert results["index"]["chunks"] > 0
    assert len(results["graph"]) > 0
    # Grounding: real tuples, zero unresolved ids, zero chronology violations.
    grounding = results["grounding"]
    assert grounding["aligned_tuples"] > 0
    assert grounding["evidence_resolution_rate"] == 1.0        # gate G2
    assert grounding["chronology_violations"] == 0
    assert grounding["incidents_grounded"] == 3                # workspace bursts


def test_e2e_artifacts_are_consistent(grounded_workspace):
    cfg, _results = grounded_workspace
    tuples = pd.read_parquet(Path(cfg.paths.data_processed) / "aligned_tuples.parquet")
    features = pd.read_parquet(cfg.paths.sensor_features_index)
    # Every grounded window exists in the feature table with the same span.
    joined = tuples.merge(features, on=["window_id"], suffixes=("_t", "_f"))
    assert len(joined) == len(tuples)
    assert (joined["t_start_t"] == joined["t_start_f"]).all()
    # Evidence ids parse and include the window itself + a retrieved chunk.
    ids = json.loads(tuples.iloc[0]["evidence_ids"])
    assert tuples.iloc[0]["window_id"] in ids
    assert any(i.startswith("doc_") for i in ids)
    # Retrieval text/citation are populated from the real (fallback) index.
    assert tuples["retrieved_citation"].str.contains("§").all()


def test_e2e_ui_helpers_render_grounded_output(grounded_workspace):
    cfg, _results = grounded_workspace
    tuples = pd.read_parquet(Path(cfg.paths.data_processed) / "aligned_tuples.parquet")
    features = pd.read_parquet(cfg.paths.sensor_features_index)
    incident_id = str(tuples["incident_id"].iloc[0])

    rows = incident_tuples(tuples, incident_id)
    assert not rows.empty
    events = grounded_sop_events(rows, rel_offset=3.0, t0=0.0, t1=5.0)
    assert events and all(e.source == "grounded" for e in events)
    sentences = grounded_explanation(rows)
    assert sentences and all(s["source"] == "incident" for s in sentences)

    feature_rows = incident_feature_rows(features, incident_id)
    assert not feature_rows.empty                       # sensor table populated


def test_e2e_fusion_builds_bundles_and_contexts(grounded_workspace, monkeypatch):
    """Build-A: evidence bundles + decoder contexts over the grounded workspace."""
    cfg, _results = grounded_workspace
    from src.fusion import select as fusion_mod
    monkeypatch.setattr(fusion_mod, "append_run_record", lambda *_a, **_k: None)
    summary = fusion_mod.build_bundles(cfg, write=True)
    assert summary["incidents_bundled"] == 3
    assert summary["resolution_rate"] == 1.0
    assert summary["modality_counts"].get("sensor", 0) >= 3
    assert summary["modality_counts"].get("document", 0) >= 3

    processed = Path(cfg.paths.data_processed)
    items = pd.read_parquet(processed / "evidence_bundles.parquet")
    contexts = pd.read_parquet(processed / "decoder_contexts.parquet")
    # Ranks are contiguous from 0 within each incident+modality.
    for (_inc, _mod), group in items.groupby(["incident_id", "modality"]):
        assert sorted(group["rank"]) == list(range(len(group)))
    # Context is the decoder-ready block with all sections present.
    ctx = str(contexts.iloc[0]["context_text"])
    for section in ("INCIDENT", "SENSOR CHRONOLOGY", "VIDEO", "DOCUMENTS"):
        assert section in ctx
    # UI helper consumes the bundle frame.
    from src.ui.workbench import incident_bundle
    rows = incident_bundle(items, str(items["incident_id"].iloc[0]))
    assert not rows.empty and rows.iloc[0]["modality"] == "sensor"


def test_e2e_grounding_refuses_broken_graph(grounded_workspace, monkeypatch):
    """Deleting a node from the graph must make grounding fail loudly (I-2)."""
    cfg, _results = grounded_workspace
    from src.graph.evidence_graph import EvidenceGraph
    graph = EvidenceGraph.load(graph_path(cfg))
    a_window = next(n for n, d in graph.g.nodes(data=True)
                    if d.get("kind") == "window")
    graph.g.remove_node(a_window)
    graph.save(graph_path(cfg))
    with pytest.raises(KeyError):
        grounding_mod.ground_corpus(cfg, write=False)
