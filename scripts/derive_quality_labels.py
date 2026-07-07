"""Recover the real good/bad folder labels for existing incidents.

The generic_csv reader surfaces the raw run's good/bad parent folder as
meta['quality'], but the label was never persisted and run_id is hashed into
the incident id. Since the whole ETL is deterministic, re-running the reader +
detector re-derives exactly the same incident ids — letting us attach the
REAL run-level quality label to every existing incident without rebuilding
any artifact.

Writes docs/_data/quality_labels.jsonl: {"incident_id", "quality", "run_id"}.
These are run-level labels (each incident inherits its source run's label),
not window-level ground truth — the caveat travels in the file header line.

Usage:
    python scripts/derive_quality_labels.py --config config/dataset.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.common.config import load_config
from src.common.ids import incident_id
from src.etl.sensor_etl import SensorETL, read_generic_csv

DEFAULT_OUT = Path("docs/_data/quality_labels.jsonl")


def derive(config: str, out_path: Path, limit: int | None = None) -> dict:
    cfg = load_config(config)
    etl = SensorETL(cfg)
    records = []
    for dscfg in cfg.sensor.datasets:
        if not dscfg.enabled or dscfg.reader != "generic_csv":
            continue
        root = Path(cfg.resolve(dscfg.path))
        for run in read_generic_csv(root, dscfg, etl.log):
            if run.meta.get("quality") is None:
                continue
            df_r = etl.normalizer.rename_and_select(run.df, dscfg.column_map)
            fs = etl.fs_estimator.estimate(df_r, run.meta, dscfg.fs_hz)
            df = etl.normalizer.build_time(df_r, fs)
            events = etl.detector.detect(df, fs, cfg.sensor.event_detection)
            max_w = cfg.sensor.windowing.max_windows_per_run
            if max_w is not None:
                events = events[:max_w]
            for ev in events:
                records.append({
                    "incident_id": incident_id(dscfg.name, run.run_id, ev.t_event_s),
                    "quality": str(run.meta["quality"]),
                    "run_id": run.run_id,
                })
            if limit and len(records) >= limit:
                break
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
    counts: dict[str, int] = {}
    for record in records:
        counts[record["quality"]] = counts.get(record["quality"], 0) + 1
    return {"incidents_labeled": len(records), "by_quality": counts,
            "out": out_path.as_posix(),
            "note": "run-level labels: every incident inherits its raw run's "
                    "good/bad folder; not window-level ground truth"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recover good/bad labels.")
    parser.add_argument("--config", default="config/dataset.yaml")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)
    print(json.dumps(derive(args.config, args.out, args.limit), indent=2,
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
