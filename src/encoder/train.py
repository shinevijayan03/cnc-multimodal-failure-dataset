"""Encoder training/inference entrypoint (Build Phase 4).

Trains on the TRAIN split only, evaluates on VAL (test is quarantined, I-4),
writes Hvib embeddings + anomaly scores for train+val windows, saves the
checkpoint, and appends a seeded run record to docs/_eval/runs.jsonl (I-5).

The AUROC computed here is a TRAINING DIAGNOSTIC against the recovered
good/bad folder labels (scripts/derive_quality_labels.py) — real labels, but
run-level (every window of a run inherits its label). The official KPI gates
in src/eval/ are untouched (I-6).

Usage:
    python -m src.encoder.train --config config/dataset.yaml --seed 20260702
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from src.common.config import PipelineConfig, load_config
from src.common.io_utils import write_parquet_atomic
from src.encoder.base import build_encoder
from src.encoder.data import build_token_cache, load_tokens, tokens_path
from src.eval.run import _git_sha, _hash_payload, append_run_record

QUALITY_LABELS = Path("docs/_data/quality_labels.jsonl")
MODELS_DIR = Path("models")
HVIB_FILENAME = "hvib.parquet"


def auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Rank-based AUROC (ties averaged). Training diagnostic, not a KPI gate."""
    scores = np.asarray(scores, dtype="float64")
    labels = np.asarray(labels, dtype="int64")
    n_pos = int(labels.sum())
    n_neg = int(len(labels) - n_pos)
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(scores)
    ranks = np.empty(len(scores), dtype="float64")
    sorted_scores = scores[order]
    i = 0
    while i < len(scores):
        j = i
        while j + 1 < len(scores) and sorted_scores[j + 1] == sorted_scores[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return float((ranks[labels == 1].sum() - n_pos * (n_pos + 1) / 2.0)
                 / (n_pos * n_neg))


def load_quality_labels(path: Path = QUALITY_LABELS) -> dict[str, int]:
    """incident_id -> 1 (bad) / 0 (good), from the recovered folder labels."""
    if not path.exists():
        return {}
    labels: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        labels[str(record["incident_id"])] = 1 if record["quality"] == "bad" else 0
    return labels


def _heuristic_scores(cfg: PipelineConfig, window_ids: pd.Series) -> np.ndarray | None:
    """Phase 3 heuristic anomaly scores aligned to *window_ids* (comparison floor)."""
    path = Path(cfg.paths.sensor_features_index)
    if not path.exists():
        return None
    features = pd.read_parquet(path, columns=["window_id", "anomaly_score"])
    lookup = dict(zip(features["window_id"], features["anomaly_score"]))
    if not all(w in lookup for w in window_ids):
        return None
    return np.asarray([lookup[w] for w in window_ids], dtype="float64")


def run_training(cfg: PipelineConfig, seed: int, kind: str | None = None,
                 epochs: int | None = None, device: str | None = None,
                 limit: int | None = None, write: bool = True) -> dict:
    enc_cfg = cfg.encoder
    kind = kind or enc_cfg.kind
    if not tokens_path(cfg).exists():
        build_token_cache(cfg, limit=limit)

    x_train, meta_train = load_tokens(cfg, ("train",))
    x_val, meta_val = load_tokens(cfg, ("val",))
    if x_train.size == 0 or x_val.size == 0:
        raise RuntimeError("no train/val tokens — run the pipeline + subwindow/"
                           "token builds first")

    encoder = build_encoder(kind, token_dim=x_train.shape[1], dim=enc_cfg.dim,
                            seed=seed, device=device or enc_cfg.device,
                            hidden=enc_cfg.hidden,
                            epochs=epochs or enc_cfg.epochs,
                            batch_size=enc_cfg.batch_size, lr=enc_cfg.lr)
    fit_metrics = encoder.fit(x_train)

    scores_val = encoder.anomaly_scores(x_val)
    metrics: dict = {**fit_metrics,
                     "val_windows": int(len(x_val)),
                     "val_anomaly_mean": round(float(scores_val.mean()), 6)}
    if kind == "autoencoder":
        metrics["val_recon_mse_mean"] = round(float(
            encoder._recon_errors(x_val).mean()), 6)  # noqa: SLF001 - diagnostic

    quality = load_quality_labels()
    label_note = "no quality labels found"
    if quality:
        labels_val = np.asarray([quality.get(i, -1) for i in meta_val["incident_id"]])
        known = labels_val >= 0
        if known.any() and 0 < labels_val[known].sum() < known.sum():
            metrics["val_auroc_quality_encoder"] = round(
                auroc(scores_val[known], labels_val[known]), 4)
            metrics["val_quality_pos"] = int(labels_val[known].sum())
            metrics["val_quality_neg"] = int(known.sum() - labels_val[known].sum())
            heuristic = _heuristic_scores(cfg, meta_val["window_id"])
            if heuristic is not None:
                metrics["val_auroc_quality_heuristic"] = round(
                    auroc(heuristic[known], labels_val[known]), 4)
            label_note = ("run-level good/bad folder labels (real, recovered); "
                          "every window inherits its run label")

    # ---- persist embeddings + checkpoint ----
    if write:
        hvib_train = encoder.encode(x_train)
        hvib_val = encoder.encode(x_val)
        scores_train = encoder.anomaly_scores(x_train)
        frame = pd.concat([
            meta_train.assign(anomaly_score=scores_train,
                              hvib=[json.dumps(np.round(h, 6).tolist())
                                    for h in hvib_train]),
            meta_val.assign(anomaly_score=scores_val,
                            hvib=[json.dumps(np.round(h, 6).tolist())
                                  for h in hvib_val]),
        ], ignore_index=True)
        hvib_path = Path(cfg.paths.data_processed) / HVIB_FILENAME
        write_parquet_atomic(frame, hvib_path)
        metrics["hvib_out"] = hvib_path.as_posix()
        if hasattr(encoder, "save"):
            MODELS_DIR.mkdir(parents=True, exist_ok=True)
            ckpt = MODELS_DIR / f"encoder_{kind}_{seed}.pt"
            encoder.save(ckpt)
            metrics["checkpoint"] = ckpt.as_posix()

    ts = datetime.now(ZoneInfo("Asia/Calcutta")).isoformat(timespec="seconds")
    record = {
        "run_id": f"encoder_{kind}_{seed}_{ts.replace(':', '').replace('-', '')}",
        "ts": ts,
        "git_sha": _git_sha(),
        "config_hash": _hash_payload(enc_cfg.model_dump() | {"kind": kind}),
        "seed": seed,
        "split": "val",
        "system": f"encoder_{kind}",
        "dataset_manifest_hash": _hash_payload({
            "tokens": tokens_path(cfg).as_posix(),
            "n_train": int(len(x_train)), "n_val": int(len(x_val))}),
        "metrics": {k: v for k, v in metrics.items()
                    if isinstance(v, (int, float))},
        "gates": {},
        "notes": f"Phase 4 encoder training diagnostic; labels: {label_note}",
    }
    if write:
        append_run_record(record)
    return {"record": record, "metrics": metrics}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train the Phase 4 sensor encoder.")
    parser.add_argument("--config", default="config/dataset.yaml")
    parser.add_argument("--seed", type=int, default=20260702)
    parser.add_argument("--kind", choices=["autoencoder", "baseline"], default=None)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--device", default=None)
    parser.add_argument("--limit", type=int, default=None,
                        help="Incident limit when building the token cache")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    result = run_training(cfg, seed=args.seed, kind=args.kind, epochs=args.epochs,
                          device=args.device, limit=args.limit,
                          write=not args.no_write)
    print(json.dumps(result["metrics"], indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
