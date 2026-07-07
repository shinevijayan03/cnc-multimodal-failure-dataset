"""Integration + e2e tests — IT-SENS, IT-TEXT, IT-ASM, IT-EVAL, E2E, UT-CLI.

These run real stage ``run()`` methods over the temp `workspace` fixture (one
synthetic sensor csv with 3 bursts + a tiny markdown manual). ffmpeg is not
required: the video stage skips cleanly and the assembler tolerates a null video.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from src.common.errors import AssemblyError
from src.common.io_utils import load_json_col, read_parquet
from src.etl.assemble_incidents import IncidentAssembler
from src.etl.sensor_etl import SensorETL
from src.etl.text_etl import TextETL
from src.evaluate import compute_metrics, evaluate_build


# --------------------------------------------------------------------------- Sensor
def test_sensor_run_writes_windows(mini_cfg):  # IT-SENS-01
    summ = SensorETL(mini_cfg).run()
    assert summ.written == 3
    idx = read_parquet(mini_cfg.paths.sensor_index)
    assert len(idx) == 3
    files = list(Path(mini_cfg.paths.sensor_windows_dir).glob("*.parquet"))
    assert len(files) == 3
    window = read_parquet(files[0])
    assert "t_rel_s" in window.columns and "az" in window.columns


def test_sensor_dry_run_writes_nothing(mini_cfg):  # IT-SENS-02
    summ = SensorETL(mini_cfg).run(dry_run=True)
    assert summ.written == 3                                 # intended count reported
    assert not Path(mini_cfg.paths.sensor_index).exists()
    assert not list(Path(mini_cfg.paths.sensor_windows_dir).glob("*.parquet"))


def test_sensor_disabled_dataset_skipped(mini_cfg):  # IT-SENS-03
    summ = SensorETL(mini_cfg).run()
    assert summ.skipped >= 1                                 # the disabled_ds dataset


def test_sensor_idempotent_rerun(mini_cfg):  # IT-SENS-04
    SensorETL(mini_cfg).run()
    ids1 = set(read_parquet(mini_cfg.paths.sensor_index)["incident_id"])
    SensorETL(mini_cfg).run()
    ids2 = set(read_parquet(mini_cfg.paths.sensor_index)["incident_id"])
    assert ids1 == ids2 and len(ids1) == 3


# --------------------------------------------------------------------------- Text
def test_text_run_writes_chunks(mini_cfg):  # IT-TEXT-01
    summ = TextETL(mini_cfg).run()
    assert summ.written >= 2
    chunks = read_parquet(mini_cfg.paths.text_chunks)
    assert set(chunks["doc_type"]).issubset({"sop", "maintenance"})
    assert chunks["chunk_id"].is_unique
    assert {"sop", "maintenance"} & set(chunks["doc_type"])  # at least one type present


# --------------------------------------------------------------------------- Assemble
def _build_upstream(cfg):
    SensorETL(cfg).run()
    TextETL(cfg).run()


def test_assemble_from_fixtures(mini_cfg):  # IT-ASM-01 / IT-ASM-02
    _build_upstream(mini_cfg)
    summ = IncidentAssembler(mini_cfg).run()
    assert summ.written == 3
    inc = read_parquet(mini_cfg.paths.incidents_index)
    chunks = set(read_parquet(mini_cfg.paths.text_chunks)["chunk_id"])
    for _, r in inc.iterrows():
        # JSON fields parse
        sop = load_json_col(r["sop_chunk_ids"])
        maint = load_json_col(r["maintenance_chunk_ids"])
        spans = load_json_col(r["sensor_relevant_spans"])
        assert isinstance(spans, list)
        # referential integrity (IT-ASM-02)
        for c in sop + maint:
            assert c in chunks
        assert r["split"] in {"train", "val", "test", "human_eval"}


def test_assemble_missing_upstream_fail_fast(mini_cfg):  # IT-ASM-03
    with pytest.raises(AssemblyError) as exc:
        IncidentAssembler(mini_cfg).run()
    assert "sensor" in str(exc.value).lower()


def test_incident_without_video_flagged(mini_cfg):  # IT-ASM-04
    _build_upstream(mini_cfg)                                # no video index built
    summ = IncidentAssembler(mini_cfg).run()
    assert summ.notes["no_video"] == 3
    inc = read_parquet(mini_cfg.paths.incidents_index)
    assert inc["video_file"].isna().all()


# --------------------------------------------------------------------------- Evaluate
def test_eval_metrics_on_fixture(mini_cfg):  # IT-EVAL-01
    _build_upstream(mini_cfg)
    IncidentAssembler(mini_cfg).run()
    rep = evaluate_build(mini_cfg, tier="mvp", write=True)
    assert rep.metrics["n_incidents"] == 3
    assert rep.metrics["pct_with_sop_and_maint"] == 1.0
    assert rep.metrics["pct_missing_sensor_file"] == 0.0
    assert rep.metrics["pct_dangling_chunk_id"] == 0.0
    assert (Path(mini_cfg.paths.data_processed) / "eval_report.json").exists()


def test_eval_detects_malformed_json(mini_cfg):  # IT-EVAL-02
    _build_upstream(mini_cfg)
    IncidentAssembler(mini_cfg).run()
    inc = read_parquet(mini_cfg.paths.incidents_index)
    # inject a bad span (end < start) by editing the JSON cell
    inc.loc[0, "sensor_relevant_spans"] = '[{"start_s": 5.0, "end_s": 1.0}]'
    rep = compute_metrics(inc, None, None,
                          read_parquet(mini_cfg.paths.text_chunks), mini_cfg, "mvp")
    assert rep.metrics["pct_bad_span"] > 0


# --------------------------------------------------------------------------- E2E
def test_e2e_demo_build(mini_cfg):  # E2E-01
    SensorETL(mini_cfg).run()
    TextETL(mini_cfg).run()
    # video stage skipped (no ffmpeg) — assembler tolerates it
    IncidentAssembler(mini_cfg).run()
    inc = read_parquet(mini_cfg.paths.incidents_index)
    assert len(inc) >= 1
    assert not inc["incident_id"].duplicated().any()
    assert inc["split"].notna().all()


def test_e2e_determinism_rerun(mini_cfg):  # E2E-02
    def build():
        SensorETL(mini_cfg).run()
        TextETL(mini_cfg).run()
        IncidentAssembler(mini_cfg).run()
        return read_parquet(mini_cfg.paths.incidents_index)

    a = build()
    b = build()
    assert list(a["incident_id"]) == list(b["incident_id"])
    assert list(a["split"]) == list(b["split"])


# --------------------------------------------------------------------------- CLI
def test_cli_dry_run_exit_zero(workspace):  # UT-CLI-01
    from typer.testing import CliRunner

    from src.cli import app
    cfg = str(workspace / "config" / "dataset.yaml")
    res = CliRunner().invoke(app, ["sensor", "--config", cfg, "--dry-run"])
    assert res.exit_code == 0


def test_cli_missing_upstream_nonzero(workspace):  # UT-CLI-02
    from typer.testing import CliRunner

    from src.cli import app
    cfg = str(workspace / "config" / "dataset.yaml")
    res = CliRunner().invoke(app, ["assemble", "--config", cfg])
    assert res.exit_code != 0


def test_cli_limit_honored(workspace):  # UT-CLI-03
    from typer.testing import CliRunner

    from src.cli import app
    cfg = str(workspace / "config" / "dataset.yaml")
    res = CliRunner().invoke(app, ["sensor", "--config", cfg, "--limit", "1"])
    assert res.exit_code == 0
    idx = read_parquet(load_config_path(workspace).paths.sensor_index)
    # one run had 3 bursts -> up to 3 windows from the single processed run
    assert len(idx) >= 1


def load_config_path(workspace):
    from src.common.config import load_config
    return load_config(workspace / "config" / "dataset.yaml")
