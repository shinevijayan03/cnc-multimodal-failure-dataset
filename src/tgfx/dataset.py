"""Build TGFX manifest, alignment ledger, and split ID scaffolding.

This module consumes existing Recipe A Parquet artifacts. It does not change raw
data, Parquet schemas, IDs, labels, or split assignment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from src.common.config import PipelineConfig, load_config
from src.common.io_utils import load_json_col, read_parquet

DEFAULT_MANIFEST = Path("docs/_data/manifest.json")
DEFAULT_LEDGER = Path("docs/_data/alignment_ledger.jsonl")
DEFAULT_SPLITS = Path("data/splits")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return "UNKNOWN"


def _schema(frame: pd.DataFrame) -> list[str]:
    return [str(col) for col in frame.columns]


def artifact_record(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    record: dict[str, Any] = {
        "path": path.as_posix(),
        "exists": path.exists(),
    }
    if not path.exists():
        return record
    record["sha256"] = sha256_file(path)
    if path.suffix.lower() == ".parquet":
        frame = read_parquet(path)
        record["rows"] = int(len(frame))
        record["schema"] = _schema(frame)
    else:
        record["bytes"] = path.stat().st_size
    return record


def _safe_list(value: Any) -> list:
    return [str(item) for item in load_json_col(value)]


def build_alignment_records(incidents: pd.DataFrame) -> list[dict[str, Any]]:
    records = []
    for _, row in incidents.iterrows():
        records.append({
            "incident_id": str(row["incident_id"]),
            "split": str(row["split"]),
            "sensor_file": str(row["sensor_file"]),
            "sensor_spans": load_json_col(row.get("sensor_relevant_spans")),
            "video_file": None if pd.isna(row.get("video_file")) else str(row.get("video_file")),
            "video_spans": load_json_col(row.get("video_relevant_spans")),
            "sop_chunk_ids": _safe_list(row.get("sop_chunk_ids")),
            "maintenance_chunk_ids": _safe_list(row.get("maintenance_chunk_ids")),
            "alignment_method": str(row.get("alignment_method", "unknown")),
            "sync_provenance": "constructed",
            "label_status": "weak_signal_derived",
        })
    return records


def build_split_records(incidents: pd.DataFrame) -> dict[str, list[dict[str, str]]]:
    splits: dict[str, list[dict[str, str]]] = {}
    for _, row in incidents.iterrows():
        split = str(row["split"])
        splits.setdefault(split, []).append({
            "incident_id": str(row["incident_id"]),
            "failure_family": str(row["failure_family"]),
            "source_dataset": str(row["source_dataset"]),
        })
    return splits


def build_manifest(cfg: PipelineConfig, incidents: pd.DataFrame) -> dict[str, Any]:
    processed = Path(cfg.paths.data_processed)
    artifacts = {
        "incidents": artifact_record(cfg.paths.incidents_index),
        "sensor_index": artifact_record(cfg.paths.sensor_index),
        "text_chunks": artifact_record(cfg.paths.text_chunks),
        "video_index": artifact_record(cfg.paths.video_index),
    }
    return {
        "version": 1,
        "generated_at": datetime.now(ZoneInfo("Asia/Calcutta")).isoformat(timespec="seconds"),
        "git_sha": _git_sha(),
        "config": "config/dataset.yaml",
        "source": "Recipe A processed artifacts",
        "label_status": "weak_signal_derived_not_ground_truth",
        "test_quarantine": "split files list IDs/provenance only; model code must not consume test rows",
        "counts": {
            "incidents": int(len(incidents)),
            "splits": {str(k): int(v) for k, v in incidents["split"].value_counts().to_dict().items()},
            "failure_family": {
                str(k): int(v)
                for k, v in incidents["failure_family"].value_counts().to_dict().items()
            },
        },
        "artifacts": artifacts,
        "processed_dir": processed.as_posix(),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, sort_keys=True) + "\n")


def build_dataset(
    config: str | Path = "config/dataset.yaml",
    manifest_path: Path = DEFAULT_MANIFEST,
    ledger_path: Path = DEFAULT_LEDGER,
    splits_dir: Path = DEFAULT_SPLITS,
) -> dict[str, Any]:
    cfg = load_config(config)
    incidents = read_parquet(cfg.paths.incidents_index)
    manifest = build_manifest(cfg, incidents)
    ledger = build_alignment_records(incidents)
    splits = build_split_records(incidents)

    write_json(manifest_path, manifest)
    write_jsonl(ledger_path, ledger)
    splits_dir.mkdir(parents=True, exist_ok=True)
    for split, rows in sorted(splits.items()):
        write_jsonl(splits_dir / f"{split}.jsonl", rows)

    return {
        "manifest": manifest_path.as_posix(),
        "ledger": ledger_path.as_posix(),
        "splits_dir": splits_dir.as_posix(),
        "n_incidents": int(len(incidents)),
        "splits": {name: len(rows) for name, rows in sorted(splits.items())},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build TGFX dataset substrate files.")
    parser.add_argument("--config", default="config/dataset.yaml")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--splits-dir", type=Path, default=DEFAULT_SPLITS)
    args = parser.parse_args(argv)
    summary = build_dataset(args.config, args.manifest, args.ledger, args.splits_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
