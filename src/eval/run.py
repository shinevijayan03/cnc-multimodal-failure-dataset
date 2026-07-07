"""TGFX evaluation entrypoint.

Usage:
    python -m src.eval.run --fixtures oracle
    python -m src.eval.run --fixtures corrupted_intervals
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.eval.fixtures import load_fixture
from src.eval.metrics import compute_metrics

DEFAULT_SEED = 20260702
RUNS_PATH = Path("docs/_eval/runs.jsonl")


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001 - run records must still be emitted outside git
        return "UNKNOWN"


def _hash_payload(payload: object) -> str:
    data = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def build_run_record(fixture_name: str, split: str, system: str, seed: int) -> dict:
    fixture = load_fixture(fixture_name)
    metrics = compute_metrics(fixture.outputs, fixture.gold)
    ts = datetime.now(ZoneInfo("Asia/Calcutta")).isoformat(timespec="seconds")
    ts_id = ts.replace(":", "").replace("-", "")
    return {
        "run_id": f"fixture_{fixture_name}_{seed}_{ts_id}",
        "ts": ts,
        "git_sha": _git_sha(),
        "config_hash": _hash_payload({"fixture": fixture_name, "system": system}),
        "seed": seed,
        "split": split,
        "system": system,
        "dataset_manifest_hash": _hash_payload({"gold": fixture.name, "n": len(fixture.gold)}),
        "metrics": metrics,
        "gates": {
            "G1": metrics["schema_valid_rate"] == 1.0,
            "G2": metrics["attr_precision"] >= 0.95,
        },
        "notes": "fixture evaluation harness smoke run",
    }


def append_run_record(record: dict, path: Path = RUNS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run TGFX fixture evaluation.")
    parser.add_argument("--fixtures", default="oracle", choices=["oracle", "corrupted_intervals"])
    parser.add_argument("--split", default="val")
    parser.add_argument("--system", default="fixture_oracle")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--no-write", action="store_true", help="Do not append docs/_eval/runs.jsonl")
    args = parser.parse_args(argv)

    record = build_run_record(args.fixtures, args.split, args.system, args.seed)
    if not args.no_write:
        append_run_record(record)
    print(json.dumps(record["metrics"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
