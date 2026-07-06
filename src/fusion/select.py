"""Evidence selection head + multimodal context builder (Build-A, v1).

Deterministic v1 per decision D8 (fusion honesty): no trainable
cross-attention yet. Per incident it ranks REAL evidence from Phases 2-7:

  sensor    — SW_* sub-windows scored by max(encoder, heuristic) anomaly
  video     — the linked clip's frozen-VLM summary, scored by its confidence
  documents — runtime-retriever hits (BGE cosine + failure-topic boost)

Every selected evidence_id must resolve in the evidence graph (I-2) — an
unresolvable id raises. The context builder emits the exact text block the
Build-B decoder will receive, so the decoder phase starts contract-ready.

Usage:
    python -m src.fusion.select --config config/dataset.yaml [--limit N]
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from src.common.config import PipelineConfig, load_config
from src.common.io_utils import read_parquet, write_parquet_atomic
from src.eval.run import _git_sha, _hash_payload, append_run_record
from src.graph.evidence_graph import EvidenceGraph, graph_path
from src.retrieval.embeddings import build_embedder
from src.retrieval.retriever import IncidentRetriever
from src.retrieval.store import VectorStore
from src.ui.workbench import incident_feature_rows, incident_tuples

BUNDLES_FILENAME = "evidence_bundles.parquet"
CONTEXTS_FILENAME = "decoder_contexts.parquet"
TOP_K_SENSOR = 3
TOP_K_DOCS = 3


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    modality: str             # sensor | video | document
    rank: int                 # 0 = strongest within its modality
    score: float              # selection score (modality-specific semantics)
    confidence: float         # raw model/retriever confidence
    label: str                # human-readable one-liner
    detail: str = ""


@dataclass(frozen=True)
class EvidenceBundle:
    incident_id: str
    items: list[EvidenceItem]
    context_text: str
    caveats: list[str] = field(default_factory=list)

    def ids(self) -> list[str]:
        return [item.evidence_id for item in self.items]

    def by_modality(self, modality: str) -> list[EvidenceItem]:
        return [i for i in self.items if i.modality == modality]


def _sensor_items(feature_rows: pd.DataFrame, tuple_rows: pd.DataFrame,
                  k: int = TOP_K_SENSOR) -> list[EvidenceItem]:
    summary_by_window = dict(zip(tuple_rows["window_id"],
                                 tuple_rows["sensor_summary"])) \
        if not tuple_rows.empty else {}
    alarm_by_window = dict(zip(tuple_rows["window_id"],
                               tuple_rows["alarm_state"])) \
        if not tuple_rows.empty else {}
    scored = []
    for _, row in feature_rows.iterrows():
        enc = row.get("anomaly_encoder")
        heur = float(row.get("anomaly_heuristic", 0.0) or 0.0)
        enc_val = float(enc) if enc is not None and pd.notna(enc) else None
        score = max(heur, enc_val or 0.0)
        confidence = enc_val if enc_val is not None else heur
        scored.append((score, confidence, row))
    # Deterministic: score desc, then window_id asc as tie-break.
    scored.sort(key=lambda t: (-t[0], str(t[2]["window_id"])))
    items = []
    for rank, (score, confidence, row) in enumerate(scored[:k]):
        window_id = str(row["window_id"])
        items.append(EvidenceItem(
            evidence_id=window_id, modality="sensor", rank=rank,
            score=round(score, 6), confidence=round(confidence, 6),
            label=(f"{window_id} [{row['t_start']:+.1f}s..{row['t_end']:+.1f}s] "
                   f"{alarm_by_window.get(window_id, '')}"),
            detail=str(summary_by_window.get(window_id, ""))))
    return items


def _video_item(incident: pd.Series, summary_row: pd.Series | None
                ) -> list[EvidenceItem]:
    video_file = incident.get("video_file")
    if video_file is None or pd.isna(video_file) or not str(video_file):
        return []
    if summary_row is None:
        return [EvidenceItem(
            evidence_id=str(video_file), modality="video", rank=0,
            score=0.3, confidence=0.3,
            label=f"label-matched clip {video_file}",
            detail="no VLM summary built for this clip")]
    labels = ", ".join(json.loads(summary_row["visual_labels"]) or [])
    return [EvidenceItem(
        evidence_id=str(video_file), modality="video", rank=0,
        score=float(summary_row["confidence"]),
        confidence=float(summary_row["confidence"]),
        label=f"{summary_row['mode'].upper()} clip: {labels or 'no labels'}",
        detail=str(summary_row["summary"]))]


def _document_items(retrieved: list, k: int = TOP_K_DOCS) -> list[EvidenceItem]:
    items = []
    for rank, hit in enumerate(retrieved[:k]):
        items.append(EvidenceItem(
            evidence_id=hit.evidence_id, modality="document", rank=rank,
            score=round(hit.boosted_score, 6), confidence=round(hit.score, 6),
            label=hit.citation,
            detail=" ".join(hit.text.split())[:200]))
    return items


def build_context(incident: pd.Series, bundle_items: list[EvidenceItem],
                  tuple_rows: pd.DataFrame) -> str:
    """The decoder-facing multimodal context block (Build-B consumes this)."""
    lines = [
        f"INCIDENT {incident.get('incident_id')} | "
        f"failure_family={incident.get('failure_family', 'unknown')} | "
        f"severity={incident.get('severity_label', 'unknown')} | "
        f"mode_state={incident.get('regime_label', 'unknown')} | "
        f"event anchored at t=0s",
        "SENSOR CHRONOLOGY (real, per sub-window):",
    ]
    for item in [i for i in bundle_items if i.modality == "sensor"]:
        lines.append(f"- [{item.evidence_id} | score {item.score:.3f}] "
                     f"{item.label}: {item.detail}")
    video = [i for i in bundle_items if i.modality == "video"]
    lines.append("VIDEO (sync_provenance: constructed — no within-incident "
                 "timestamps):")
    lines += [f"- [{i.evidence_id} | conf {i.confidence:.2f}] {i.label}: "
              f"{i.detail}" for i in video] or ["- none"]
    lines.append("DOCUMENTS (vector retrieval, cosine + topic boost):")
    docs = [i for i in bundle_items if i.modality == "document"]
    lines += [f"- [{i.label} | score {i.score:.3f}] {i.detail}"
              for i in docs] or ["- none"]
    if not tuple_rows.empty:
        spans = ", ".join(f"{r['window_id']}({r['alarm_state']})"
                          for _, r in tuple_rows.iterrows())
        lines.append(f"ALARM STATES: {spans}")
    return "\n".join(lines)


def select_evidence(incident: pd.Series, feature_rows: pd.DataFrame,
                    tuple_rows: pd.DataFrame, retrieved: list,
                    graph: EvidenceGraph,
                    video_summary_row: pd.Series | None = None
                    ) -> EvidenceBundle:
    items = (_sensor_items(feature_rows, tuple_rows)
             + _video_item(incident, video_summary_row)
             + _document_items(retrieved))
    unresolved = [i.evidence_id for i in items if not graph.resolves(i.evidence_id)]
    if unresolved:
        raise KeyError(f"unresolvable evidence ids in bundle (I-2): {unresolved}")
    caveats = ["video sync constructed (I-8)"]
    if any(i.modality == "sensor" and pd.isna(i.confidence) for i in items):
        caveats.append("some sensor windows lack encoder scores")
    context = build_context(incident, items, tuple_rows)
    return EvidenceBundle(incident_id=str(incident.get("incident_id")),
                          items=items, context_text=context, caveats=caveats)


# --------------------------------------------------------------------------- #
# Corpus driver
# --------------------------------------------------------------------------- #
def build_bundles(cfg: PipelineConfig, limit: int | None = None,
                  write: bool = True, k_docs: int = TOP_K_DOCS) -> dict:
    incidents = read_parquet(cfg.paths.incidents_index)
    features = read_parquet(cfg.paths.sensor_features_index)
    processed = Path(cfg.paths.data_processed)
    hvib_path = processed / "hvib.parquet"
    hvib = read_parquet(hvib_path) if hvib_path.exists() else pd.DataFrame()
    tuples = read_parquet(processed / "aligned_tuples.parquet")
    summaries_path = processed / "video_summaries.parquet"
    summaries = (read_parquet(summaries_path) if summaries_path.exists()
                 else pd.DataFrame())
    summary_by_file = ({str(r["video_file"]): r for _, r in summaries.iterrows()}
                       if not summaries.empty else {})
    graph = EvidenceGraph.load(graph_path(cfg))
    store = VectorStore.load(cfg.paths.vector_store)
    kind = "hashing" if store.embedder_name == "hashing_fallback" else "bge"
    embedder = build_embedder(kind, model_name=cfg.retrieval.model_name,
                              device=cfg.retrieval.device,
                              batch_size=cfg.retrieval.batch_size)
    retriever = IncidentRetriever(store, embedder,
                                  cfg.assemble.text_retrieval.failure_to_topics)

    item_rows: list[dict] = []
    context_rows: list[dict] = []
    incident_frame = incidents.head(limit) if limit else incidents
    for _, incident in incident_frame.iterrows():
        inc_id = str(incident["incident_id"])
        feature_rows = incident_feature_rows(features, inc_id, hvib)
        if feature_rows.empty:
            continue
        tuple_rows = incident_tuples(tuples, inc_id)
        summary_row = summary_by_file.get(str(incident.get("video_file")))
        clip_text = str(summary_row["summary"]) if summary_row is not None else None
        retrieved = retriever.retrieve(incident, feature_rows, k=k_docs,
                                       clip_summary=clip_text)
        bundle = select_evidence(incident, feature_rows, tuple_rows, retrieved,
                                 graph, summary_row)
        for item in bundle.items:
            item_rows.append({"incident_id": inc_id, **asdict(item)})
        context_rows.append({"incident_id": inc_id,
                             "context_text": bundle.context_text,
                             "caveats": json.dumps(bundle.caveats),
                             "n_items": len(bundle.items)})

    items_frame = pd.DataFrame(item_rows)
    contexts_frame = pd.DataFrame(context_rows)
    if write and not items_frame.empty:
        write_parquet_atomic(items_frame, processed / BUNDLES_FILENAME)
        write_parquet_atomic(contexts_frame, processed / CONTEXTS_FILENAME)

    metrics = {
        "incidents_bundled": int(contexts_frame["incident_id"].nunique())
        if len(contexts_frame) else 0,
        "evidence_items": int(len(items_frame)),
        "items_per_incident_mean": round(float(contexts_frame["n_items"].mean()), 2)
        if len(contexts_frame) else 0.0,
        "resolution_rate": 1.0 if len(items_frame) else 0.0,  # unresolvables raise
        "modality_counts": items_frame["modality"].value_counts().to_dict()
        if len(items_frame) else {},
    }
    if write and len(items_frame):
        ts = datetime.now(ZoneInfo("Asia/Calcutta")).isoformat(timespec="seconds")
        append_run_record({
            "run_id": f"fusion_v1_{ts.replace(':', '').replace('-', '')}",
            "ts": ts, "git_sha": _git_sha(),
            "config_hash": _hash_payload({"k_docs": k_docs,
                                          "embedder": store.embedder_name}),
            "seed": 20260702, "split": "all_non_quarantined", "system": "fusion_v1",
            "dataset_manifest_hash": _hash_payload(
                {"items": len(items_frame),
                 "incidents": metrics["incidents_bundled"]}),
            "metrics": {k: v for k, v in metrics.items()
                        if isinstance(v, (int, float))},
            "gates": {"G2": metrics["resolution_rate"] == 1.0},
            "notes": ("deterministic evidence-selection v1 (D8): sensor by "
                      "anomaly, video by VLM confidence, documents by boosted "
                      "cosine; decoder context built per incident"),
        })
    return {**metrics,
            "bundles_out": (processed / BUNDLES_FILENAME).as_posix() if write else None,
            "contexts_out": (processed / CONTEXTS_FILENAME).as_posix() if write else None}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build evidence bundles (fusion v1).")
    parser.add_argument("--config", default="config/dataset.yaml")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--k-docs", type=int, default=TOP_K_DOCS)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    print(json.dumps(build_bundles(cfg, limit=args.limit, write=not args.no_write,
                                   k_docs=args.k_docs), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
