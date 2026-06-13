"""Stage 7 — Evaluation & dataset-quality reporting.

Computes the metrics defined in ``docs/evaluation_criteria.md`` and grades the
build PASS / WARN / FAIL for a chosen tier. Pure functions of the indices, so the
same inputs always yield the same report.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from .common.config import PipelineConfig
from .common.io_utils import load_json_col, read_parquet


# Tier thresholds (subset that gates PASS/WARN/FAIL; see evaluation_criteria.md).
TIERS: dict[str, dict[str, float]] = {
    "mvp": {
        "total_incident_hours": 2.0,
        "n_video_clips": 20,
        "text_pages_equiv": 30,
        "pct_with_sop_and_maint": 0.80,
        "pct_with_video": 0.70,
        "pct_fully_multimodal": 0.60,
        "dominant_class_share": 0.80,
        "pct_unknown_failure": 0.70,
        "entropy_failure": 0.30,
        "pct_with_sensor_span": 0.90,
        "pct_event_near_zero": 0.90,
        "pct_label_match_alignment": 0.50,
    },
    "extended": {
        "total_incident_hours": 72.0,
        "n_video_clips": 1000,
        "text_pages_equiv": 300,
        "pct_with_sop_and_maint": 0.95,
        "pct_with_video": 0.90,
        "pct_fully_multimodal": 0.85,
        "dominant_class_share": 0.50,
        "pct_unknown_failure": 0.30,
        "entropy_failure": 0.60,
        "pct_with_sensor_span": 0.98,
        "pct_event_near_zero": 0.98,
        "pct_label_match_alignment": 0.75,
    },
}

_HARD_GATES = (
    "pct_missing_sensor_file",
    "pct_missing_video_file",
    "pct_dangling_chunk_id",
    "pct_malformed_json",
    "pct_bad_span",
    "pct_duplicate_incident_id",
    "fs_hz_plausible_violations",
)


@dataclass
class MetricsReport:
    tier: str
    grade: str = "PASS"
    metrics: dict[str, Any] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"tier": self.tier, "grade": self.grade, "metrics": self.metrics,
                "failures": self.failures, "warnings": self.warnings}


def _safe_mean(series) -> float:
    return float(series.mean()) if len(series) else 0.0


def _entropy(counts: list[int]) -> float:
    total = sum(counts)
    if total == 0 or len(counts) <= 1:
        return 0.0
    probs = [c / total for c in counts if c > 0]
    h = -sum(p * math.log(p) for p in probs)
    return h / math.log(len(counts))


def compute_metrics(incidents: pd.DataFrame, sensor_idx: pd.DataFrame | None,
                    video_idx: pd.DataFrame | None, text_chunks: pd.DataFrame | None,
                    cfg: PipelineConfig, tier: str = "mvp") -> MetricsReport:
    rep = MetricsReport(tier=tier)
    m = rep.metrics
    n = len(incidents)
    m["n_incidents"] = n
    if n == 0:
        rep.grade = "FAIL"
        rep.failures.append("no incidents")
        return rep

    # Decode JSON-list columns once.
    sop = [load_json_col(v) for v in incidents["sop_chunk_ids"]]
    maint = [load_json_col(v) for v in incidents["maintenance_chunk_ids"]]
    sensor_spans = [load_json_col(v) for v in incidents["sensor_relevant_spans"]]

    # --- Scale & coverage ---
    durations = (incidents["window_end_s"] - incidents["window_start_s"]).clip(lower=0)
    m["total_incident_hours"] = round(float(durations.sum()) / 3600, 4)
    m["n_video_clips"] = int(len(video_idx)) if video_idx is not None else 0
    m["text_pages_equiv"] = round(
        float(text_chunks["n_tokens"].sum()) / 500, 2) if text_chunks is not None else 0.0
    m["n_sensor_datasets_used"] = int(incidents["source_dataset"].nunique())

    # --- Cross-modal completeness ---
    has_video = incidents["video_file"].notna()
    has_sop = pd.Series([len(s) >= 1 for s in sop])
    has_maint = pd.Series([len(s) >= 1 for s in maint])
    m["pct_with_video"] = round(_safe_mean(has_video), 4)
    m["pct_with_sop"] = round(_safe_mean(has_sop), 4)
    m["pct_with_maint"] = round(_safe_mean(has_maint), 4)
    m["pct_with_sop_and_maint"] = round(_safe_mean(has_sop & has_maint), 4)
    m["pct_fully_multimodal"] = round(
        _safe_mean(has_video.reset_index(drop=True) & has_sop & has_maint), 4)
    m["mean_sop_chunks"] = round(float(sum(len(s) for s in sop) / n), 3)
    m["mean_maint_chunks"] = round(float(sum(len(s) for s in maint) / n), 3)

    # --- Distribution & balance ---
    fam_counts = incidents["failure_family"].value_counts().to_dict()
    m["failure_family_dist"] = {k: int(v) for k, v in fam_counts.items()}
    m["regime_dist"] = {k: int(v) for k, v in
                        incidents["regime_label"].value_counts().to_dict().items()}
    m["severity_dist"] = {k: int(v) for k, v in
                          incidents["severity_label"].value_counts().to_dict().items()}
    m["split_dist"] = {k: int(v) for k, v in
                       incidents["split"].value_counts().to_dict().items()}
    m["dominant_class_share"] = round(max(fam_counts.values()) / n, 4)
    m["pct_unknown_failure"] = round(
        float((incidents["failure_family"] == "unknown").mean()), 4)
    m["entropy_failure"] = round(_entropy(list(fam_counts.values())), 4)

    # --- Integrity & sanity (hard gates) ---
    missing_sensor = sum(0 if Path(cfg.resolve(f)).exists() else 1
                         for f in incidents["sensor_file"])
    m["pct_missing_sensor_file"] = round(missing_sensor / n, 4)
    vids = incidents["video_file"].dropna()
    missing_video = sum(0 if Path(cfg.resolve(f)).exists() else 1 for f in vids)
    m["pct_missing_video_file"] = round(missing_video / len(vids), 4) if len(vids) else 0.0
    known_chunk_ids = set(text_chunks["chunk_id"]) if text_chunks is not None else set()
    dangling = sum(1 for ids in (sop + maint) for c in ids if c not in known_chunk_ids)
    m["pct_dangling_chunk_id"] = round(dangling / max(1, sum(len(x) for x in sop + maint)), 4)
    m["pct_duplicate_incident_id"] = round(
        float(incidents["incident_id"].duplicated().mean()), 4)
    # malformed json: a list col that failed to parse would have raised; recheck spans validity.
    bad_span = 0
    near_zero = 0
    with_span = 0
    span_frac_acc = []
    for i, spans in enumerate(sensor_spans):
        dur = float(durations.iloc[i]) or 1.0
        if len(spans) >= 1:
            with_span += 1
        covered = 0.0
        hit_zero = False
        for s in spans:
            st, en = s.get("start_s"), s.get("end_s")
            if st is None or en is None or en < st:
                bad_span += 1
                continue
            covered += (en - st)
            if st <= 0.0 <= en:
                hit_zero = True
        if hit_zero:
            near_zero += 1
        span_frac_acc.append(min(covered / dur, 1.0))
    m["pct_malformed_json"] = 0.0  # decode above would have raised on malformed cells
    m["pct_bad_span"] = round(bad_span / max(1, sum(len(s) for s in sensor_spans)), 4)
    tol = 1.0
    expected = cfg.sensor.windowing.pre_event_s + cfg.sensor.windowing.post_event_s
    m["pct_window_len_mismatch"] = round(
        float(((durations - expected).abs() > tol).mean()), 4)
    fs_bad = int(((incidents["fs_hz"] < cfg.sensor.fs_estimation.min_plausible_hz) |
                  (incidents["fs_hz"] > cfg.sensor.fs_estimation.max_plausible_hz)).sum())
    m["fs_hz_plausible_violations"] = fs_bad

    # --- Grounding quality ---
    m["pct_with_sensor_span"] = round(with_span / n, 4)
    m["mean_sensor_span_count"] = round(sum(len(s) for s in sensor_spans) / n, 3)
    m["mean_sensor_span_frac"] = round(sum(span_frac_acc) / n, 4)
    m["pct_event_near_zero"] = round(near_zero / n, 4)
    m["pct_label_match_alignment"] = round(
        float((incidents["alignment_method"] == "label_match").mean()), 4)

    _grade(rep, cfg)
    return rep


def _grade(rep: MetricsReport, cfg: PipelineConfig) -> None:
    m = rep.metrics
    thr = TIERS.get(rep.tier, TIERS["mvp"])

    # Hard gates: any nonzero -> FAIL.
    for gate in _HARD_GATES:
        if m.get(gate, 0):
            rep.failures.append(f"hard-gate {gate}={m[gate]} (must be 0)")

    # FAIL-level tier floors.
    if m["total_incident_hours"] < thr["total_incident_hours"]:
        rep.failures.append(
            f"total_incident_hours {m['total_incident_hours']} < {thr['total_incident_hours']}")
    if m["pct_with_sop_and_maint"] < thr["pct_with_sop_and_maint"]:
        rep.failures.append(
            f"pct_with_sop_and_maint {m['pct_with_sop_and_maint']} < {thr['pct_with_sop_and_maint']}")

    # WARN-level soft metrics.
    soft = {
        "pct_with_video": (m["pct_with_video"], ">="),
        "pct_fully_multimodal": (m["pct_fully_multimodal"], ">="),
        "dominant_class_share": (m["dominant_class_share"], "<="),
        "pct_unknown_failure": (m["pct_unknown_failure"], "<="),
        "entropy_failure": (m["entropy_failure"], ">="),
        "pct_with_sensor_span": (m["pct_with_sensor_span"], ">="),
        "pct_event_near_zero": (m["pct_event_near_zero"], ">="),
        "pct_label_match_alignment": (m["pct_label_match_alignment"], ">="),
        "n_video_clips": (m["n_video_clips"], ">="),
        "text_pages_equiv": (m["text_pages_equiv"], ">="),
    }
    for key, (val, op) in soft.items():
        target = thr[key]
        miss = (val < target) if op == ">=" else (val > target)
        if miss:
            rep.warnings.append(f"{key}={val} misses {op}{target}")

    if rep.failures:
        rep.grade = "FAIL"
    elif rep.warnings:
        rep.grade = "WARN"
    else:
        rep.grade = "PASS"


def render_report(rep: MetricsReport) -> str:
    """Human-readable markdown report."""
    lines = [f"# Recipe A — Evaluation Report ({rep.tier} tier)", "",
             f"**Grade: {rep.grade}**", ""]
    lines.append("## Metrics")
    lines.append("| metric | value |")
    lines.append("|--------|-------|")
    for k, v in rep.metrics.items():
        if isinstance(v, dict):
            v = ", ".join(f"{kk}:{vv}" for kk, vv in v.items())
        lines.append(f"| {k} | {v} |")
    if rep.failures:
        lines += ["", "## FAIL reasons"] + [f"- {x}" for x in rep.failures]
    if rep.warnings:
        lines += ["", "## Warnings"] + [f"- {x}" for x in rep.warnings]
    return "\n".join(lines)


def evaluate_build(cfg: PipelineConfig, tier: str = "mvp", write: bool = True) -> MetricsReport:
    """Load the indices, compute metrics, optionally write json+md artifacts."""
    incidents = read_parquet(cfg.paths.incidents_index)
    sensor_idx = read_parquet(cfg.paths.sensor_index) \
        if Path(cfg.paths.sensor_index).exists() else None
    video_idx = read_parquet(cfg.paths.video_index) \
        if Path(cfg.paths.video_index).exists() else None
    text_chunks = read_parquet(cfg.paths.text_chunks) \
        if Path(cfg.paths.text_chunks).exists() else None
    rep = compute_metrics(incidents, sensor_idx, video_idx, text_chunks, cfg, tier)
    if write:
        out_dir = Path(cfg.paths.data_processed)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "eval_report.json").write_text(
            json.dumps(rep.to_dict(), indent=2), encoding="utf-8")
        (out_dir / "eval_report.md").write_text(render_report(rep), encoding="utf-8")
    return rep
