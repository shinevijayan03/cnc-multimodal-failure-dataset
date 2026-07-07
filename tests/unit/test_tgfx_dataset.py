"""Tests for TGFX dataset substrate generation."""

from __future__ import annotations

import json

from src.common.io_utils import read_parquet
from src.etl.assemble_incidents import IncidentAssembler
from src.etl.sensor_etl import SensorETL
from src.etl.text_etl import TextETL
from src.tgfx.dataset import build_dataset


def test_tgfx_dataset_substrate_writes_manifest_ledger_and_splits(mini_cfg, tmp_path):
    SensorETL(mini_cfg).run()
    TextETL(mini_cfg).run()
    IncidentAssembler(mini_cfg).run()

    manifest = tmp_path / "manifest.json"
    ledger = tmp_path / "alignment_ledger.jsonl"
    splits = tmp_path / "splits"
    summary = build_dataset(
        config=tmp_path / "config" / "dataset.yaml",
        manifest_path=manifest,
        ledger_path=ledger,
        splits_dir=splits,
    )

    incidents = read_parquet(mini_cfg.paths.incidents_index)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    ledger_rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]

    assert summary["n_incidents"] == len(incidents)
    assert payload["counts"]["incidents"] == len(incidents)
    assert payload["artifacts"]["incidents"]["rows"] == len(incidents)
    assert len(ledger_rows) == len(incidents)
    assert {row["incident_id"] for row in ledger_rows} == set(incidents["incident_id"])
    assert any(splits.glob("*.jsonl"))
