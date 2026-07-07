"""Summarize every indexed clip with the frozen VLM (Build Phase 7).

Writes video_summaries.parquet: one row per video_index entry with the VLM
(or tags-only) summary, visual labels, confidence, model, and mode.

Usage:
    python -m src.vision.build_summaries --config config/dataset.yaml
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd

from src.common.config import PipelineConfig, load_config
from src.common.io_utils import read_parquet, write_parquet_atomic
from src.vision.summarizer import build_summarizer

SUMMARIES_FILENAME = "video_summaries.parquet"


def summaries_path(cfg: PipelineConfig) -> Path:
    return Path(cfg.paths.data_processed) / SUMMARIES_FILENAME


def build_video_summaries(cfg: PipelineConfig, mode: str | None = None,
                          limit: int | None = None, write: bool = True) -> dict:
    vcfg = cfg.vision
    video_index = read_parquet(cfg.paths.video_index)
    if limit:
        video_index = video_index.head(limit)
    summarizer = build_summarizer(mode or vcfg.mode, model_name=vcfg.model_name,
                                  device=vcfg.device, n_frames=vcfg.n_frames,
                                  max_new_tokens=vcfg.max_new_tokens)
    repo_root = Path(cfg.repo_root) if cfg.repo_root else Path.cwd()
    rows = []
    started = time.perf_counter()
    total = len(video_index)
    for i, (_, rec) in enumerate(video_index.iterrows(), start=1):
        print(f"[vision] clip {i}/{total}: {rec['video_file']} "
              f"({time.perf_counter() - started:.0f}s elapsed)", flush=True)
        video_file = str(rec["video_file"])
        path = Path(video_file)
        if not path.is_absolute():
            path = repo_root / path
        summary = summarizer.summarize(
            str(path), regime=str(rec.get("regime_label", "unknown")),
            condition=str(rec.get("condition_label", "unknown")))
        rows.append({
            "video_id": str(rec["video_id"]),
            "video_file": video_file,
            "summary": summary.summary,
            "visual_labels": json.dumps(summary.visual_labels),
            "confidence": summary.confidence,
            "model": summary.model,
            "mode": summary.mode,
            "frames_used": summary.frames_used,
        })
    frame = pd.DataFrame(rows)
    out = summaries_path(cfg)
    if write and not frame.empty:
        write_parquet_atomic(frame, out)
    return {
        "clips": len(frame),
        "mode_counts": frame["mode"].value_counts().to_dict() if len(frame) else {},
        "mean_confidence": round(float(frame["confidence"].mean()), 3)
        if len(frame) else 0.0,
        "seconds": round(time.perf_counter() - started, 1),
        "out": out.as_posix() if write else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build VLM clip summaries.")
    parser.add_argument("--config", default="config/dataset.yaml")
    parser.add_argument("--mode", choices=["vlm", "tags_only"], default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    print(json.dumps(build_video_summaries(cfg, mode=args.mode, limit=args.limit,
                                           write=not args.no_write),
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
