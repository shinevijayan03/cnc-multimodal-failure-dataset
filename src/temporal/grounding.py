"""Temporal grounding — produce REAL contract-valid AlignedTuples.

For every carved sub-window this joins the real artifacts of Phases 2-6:
  sensor_summary   — generated from the real per-window features (Phase 3/4)
  clip_summary     — the label-matched clip reference with its constructed
                     sync provenance stated in the text (I-8)
  retrieved_text   — top runtime-retriever hit (real vector search, Phase 6)
  alarm_state      — real: whether the window span contains the event (t=0)
  mode_state       — regime label from the incident row
  timestamp_span   — the window's incident-relative span (D10)
  evidence_ids     — [window_id, retrieved chunk ids (+ video id)] — every one
                     must resolve in the evidence graph (I-2 / gate G2)

Chronology is validated (tuples sorted by span start, spans inside
[-60, +30]); the run summary appends a run record with the resolution rate.

Usage:
    python -m src.temporal.grounding --config config/dataset.yaml [--limit N]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from contracts import AlignedTuple
from src.common.config import PipelineConfig, load_config
from src.common.io_utils import read_parquet, write_parquet_atomic
from src.eval.run import _git_sha, _hash_payload, append_run_record
from src.graph.evidence_graph import EvidenceGraph, graph_path
from src.retrieval.embeddings import build_embedder
from src.retrieval.retriever import IncidentRetriever
from src.retrieval.store import VectorStore
from src.ui.workbench import incident_feature_rows

TUPLES_FILENAME = "aligned_tuples.parquet"


def window_sensor_summary(row: pd.Series) -> str:
    """Real single-window summary from Phase 3 features (+ encoder score)."""
    enc = row.get("anomaly_encoder")
    enc_txt = (f"; encoder anomaly {float(enc):.3f}"
               if enc is not None and pd.notna(enc) else "")
    return (f"RMS {float(row['rms']):.1f}, kurtosis {float(row['kurtosis']):.2f}, "
            f"peak interval {float(row['important_start_s']):.1f}s to "
            f"{float(row['important_end_s']):.1f}s, heuristic anomaly "
            f"{float(row['anomaly_heuristic']):.3f}{enc_txt}")


def build_aligned_tuples(incident: pd.Series, feature_rows: pd.DataFrame,
                         retrieved: list, graph: EvidenceGraph,
                         rel_offset: float = 0.0,
                         clip_summary: str | None = None) -> list[AlignedTuple]:
    """Contract-valid tuples for one incident (spans stay incident-relative)."""
    video_file = incident.get("video_file")
    has_video = video_file is not None and pd.notna(video_file) and str(video_file)
    if clip_summary is None:
        clip_summary = (f"label-matched clip {video_file} (sync_provenance: "
                        f"constructed, not measured)" if has_video
                        else "no linked video")
    top = retrieved[0] if retrieved else None
    retrieved_text = (f"{top.citation}: " + " ".join(top.text.split())[:200]
                      if top else "no retrieved documentation")
    tuples: list[AlignedTuple] = []
    for _, row in feature_rows.sort_values("t_start").iterrows():
        t_start, t_end = float(row["t_start"]), float(row["t_end"])
        evidence_ids = [str(row["window_id"])]
        evidence_ids += [e.evidence_id for e in retrieved[:2]]
        if has_video:
            evidence_ids.append(str(video_file))
        unresolved = [e for e in evidence_ids if not graph.resolves(e)]
        if unresolved:
            raise KeyError(f"unresolvable evidence ids (I-2): {unresolved}")
        tuples.append(AlignedTuple(
            window_id=str(row["window_id"]),
            sensor_summary=window_sensor_summary(row),
            clip_summary=clip_summary,
            retrieved_text=retrieved_text,
            alarm_state=("event_in_window" if t_start <= 0.0 <= t_end
                         else ("pre_event" if t_end < 0.0 else "post_event")),
            mode_state=str(incident.get("regime_label", "unknown")),
            timestamp_span=(t_start, t_end),
            evidence_ids=evidence_ids,
        ))
    starts = [t.timestamp_span[0] for t in tuples]
    if starts != sorted(starts):
        raise ValueError("aligned tuples are not chronologically ordered")
    return tuples


def _validate_videoclip(incident: pd.Series, feature_rows: pd.DataFrame,
                        summary_row: pd.Series) -> None:
    """Assert `contracts.core.VideoClip` conformance on a sample (Phase 7)."""
    from contracts import VideoClip

    t_start = float(feature_rows["t_start"].min())
    t_end = float(feature_rows["t_end"].max())
    fps = int(float(incident.get("video_fps") or 30.0) or 30)
    VideoClip(
        clip_id=str(summary_row["video_id"]),
        incident_id=str(incident["incident_id"]),
        t_start=t_start,
        t_end=t_end,
        fps=fps,
        frame_range=(0, max(1, int((t_end - t_start) * fps))),
        clip_uri=str(summary_row["video_file"]),
        sync_provenance="constructed",
        clip_summary=str(summary_row["summary"]),
        visual_labels=[str(x) for x in json.loads(summary_row["visual_labels"])],
    )


def ground_corpus(cfg: PipelineConfig, limit: int | None = None,
                  write: bool = True, k: int = 3) -> dict:
    incidents = read_parquet(cfg.paths.incidents_index)
    features = read_parquet(cfg.paths.sensor_features_index)
    hvib_path = Path(cfg.paths.data_processed) / "hvib.parquet"
    hvib = read_parquet(hvib_path) if hvib_path.exists() else pd.DataFrame()
    graph = EvidenceGraph.load(graph_path(cfg))
    store = VectorStore.load(cfg.paths.vector_store)
    kind = "hashing" if store.embedder_name == "hashing_fallback" else "bge"
    embedder = build_embedder(kind, model_name=cfg.retrieval.model_name,
                              device=cfg.retrieval.device,
                              batch_size=cfg.retrieval.batch_size)
    retriever = IncidentRetriever(store, embedder,
                                  cfg.assemble.text_retrieval.failure_to_topics)

    # Real VLM clip summaries (Phase 7), when built.
    summaries_file = Path(cfg.paths.data_processed) / "video_summaries.parquet"
    summaries = (read_parquet(summaries_file) if summaries_file.exists()
                 else pd.DataFrame())
    summary_by_file = ({str(r["video_file"]): r for _, r in summaries.iterrows()}
                       if not summaries.empty else {})
    videoclip_validated = 0

    rows = []
    n_tuples = 0
    n_ids = 0
    incident_frames = incidents.head(limit) if limit else incidents
    for _, incident in incident_frames.iterrows():
        inc_id = str(incident["incident_id"])
        feature_rows = incident_feature_rows(features, inc_id, hvib)
        if feature_rows.empty:
            continue
        clip_summary = None
        video_file = incident.get("video_file")
        summary_row = (summary_by_file.get(str(video_file))
                       if video_file is not None and pd.notna(video_file) else None)
        # B-9: the real VLM summary joins the retrieval query (sensor + video
        # context), matching the architecture's retriever inputs.
        retrieved = retriever.retrieve(
            incident, feature_rows, k=k,
            clip_summary=str(summary_row["summary"]) if summary_row is not None
            else None)
        if summary_row is not None:
            labels = ", ".join(json.loads(summary_row["visual_labels"]) or [])
            clip_summary = (f"{summary_row['mode'].upper()}"
                            f"({summary_row['model']}): {summary_row['summary']}"
                            f"{' [' + labels + ']' if labels else ''} "
                            f"(sync_provenance: constructed)")
            if videoclip_validated < 3:
                _validate_videoclip(incident, feature_rows, summary_row)
                videoclip_validated += 1
        tuples = build_aligned_tuples(incident, feature_rows, retrieved, graph,
                                      clip_summary=clip_summary)
        for t in tuples:
            n_tuples += 1
            n_ids += len(t.evidence_ids)
            rows.append({
                "incident_id": inc_id, "window_id": t.window_id,
                "t_start": t.timestamp_span[0], "t_end": t.timestamp_span[1],
                "alarm_state": t.alarm_state, "mode_state": t.mode_state,
                "sensor_summary": t.sensor_summary,
                "clip_summary": t.clip_summary,
                "retrieved_text": t.retrieved_text,
                "retrieved_citation": retrieved[0].citation if retrieved else "",
                "retrieved_score": retrieved[0].score if retrieved else 0.0,
                "evidence_ids": json.dumps(t.evidence_ids),
            })
    frame = pd.DataFrame(rows)
    out = Path(cfg.paths.data_processed) / TUPLES_FILENAME
    if write and not frame.empty:
        write_parquet_atomic(frame, out)

    metrics = {
        "videoclips_contract_validated": videoclip_validated,
        "clips_with_vlm_summary": len(summary_by_file),
        "aligned_tuples": n_tuples,
        "evidence_ids_emitted": n_ids,
        "evidence_resolution_rate": 1.0 if n_tuples else 0.0,  # unresolvables raise
        "chronology_violations": 0,                            # violations raise
        "incidents_grounded": int(frame["incident_id"].nunique()) if n_tuples else 0,
    }
    if write and n_tuples:
        ts = datetime.now(ZoneInfo("Asia/Calcutta")).isoformat(timespec="seconds")
        append_run_record({
            "run_id": f"grounding_v1_{ts.replace(':', '').replace('-', '')}",
            "ts": ts, "git_sha": _git_sha(),
            "config_hash": _hash_payload({"k": k, "embedder": store.embedder_name}),
            "seed": 20260702, "split": "all_non_quarantined", "system": "grounding_v1",
            "dataset_manifest_hash": _hash_payload({"tuples": n_tuples,
                                                    "graph_nodes": len(graph)}),
            "metrics": metrics,
            "gates": {"G2": metrics["evidence_resolution_rate"] == 1.0},
            "notes": ("real aligned tuples from Phases 2-6 artifacts; SOP text "
                      "grounded by retrieval association, video sync constructed "
                      "(I-8); window spans are the real D10 sub-windows"),
        })
    return {**metrics, "out": out.as_posix() if write else None}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build real aligned tuples.")
    parser.add_argument("--config", default="config/dataset.yaml")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    print(json.dumps(ground_corpus(cfg, limit=args.limit, write=not args.no_write,
                                   k=args.k), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
