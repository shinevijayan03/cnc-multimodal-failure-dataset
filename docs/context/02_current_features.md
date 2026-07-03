# Current Features

## Feature F-001: CLI Orchestration

Description:
- Provides CLI commands for `sensor`, `text`, `video`, `assemble`, `all`, and `evaluate`.

Status:
- Implemented and verified.

Files involved:
- `src/cli.py`, `src/common/config.py`, `src/etl/*`, `src/evaluate.py`.

Dependencies:
- `typer`, project ETL classes, project config/schema utilities.

Acceptance criteria:
- CLI help lists commands.
- Commands call the expected stages and return nonzero on documented failures.

Current implementation state:
- `python -m src.cli --help` lists all commands.

Known limitations:
- `all --dry-run --limit 2` is not the preferred quick smoke path; use per-stage dry-runs.

Related tests:
- `tests/integration/test_integration.py::test_cli_dry_run_exit_zero`
- `tests/integration/test_integration.py::test_cli_missing_upstream_nonzero`
- `tests/integration/test_integration.py::test_cli_limit_honored`

## Feature F-002: Sensor ETL

Description:
- Reads sensor datasets, normalizes channels, detects events, carves incident windows, writes sensor indexes.

Status:
- Implemented and tested.

Files involved:
- `src/etl/sensor_etl.py`, `src/common/schemas.py`, `config/dataset.yaml`.

Dependencies:
- `pandas`, `numpy`, project config/IO/schema utilities.

Acceptance criteria:
- Sensor stage creates sensor rows/windows and supports dry-run/limit.

Current implementation state:
- `sensor --dry-run --limit 2` passed with `processed=2`, `written=2`, `errors=0`.

Known limitations:
- Coverage is 74% for `src/etl/sensor_etl.py`; untested lines remain.

Related tests:
- `tests/unit/test_sensor.py`
- `tests/integration/test_integration.py::test_sensor_run_writes_windows`
- `tests/integration/test_integration.py::test_sensor_dry_run_writes_nothing`

## Feature F-003: Text ETL

Description:
- Reads manuals in configured formats, chunks text, classifies doc type, tags topics, writes `text_chunks.parquet`.

Status:
- Implemented and tested; dry-run smoke is bounded for large PDFs.

Files involved:
- `src/etl/text_etl.py`, `src/common/schemas.py`, `config/dataset.yaml`.

Dependencies:
- `tiktoken`, `pypdf`, `python-docx`; whitespace fallback exists in code.

Acceptance criteria:
- Unit/integration tests pass.
- Stage writes text chunks from fixtures.

Current implementation state:
- Tests pass.
- Current generated artifact has 934 text chunks.

Known limitations:
- `python -m src.cli text --config config/dataset.yaml --dry-run --limit 2` now completes by capping dry-run PDF pages; it still takes about 35 seconds on the current staged manuals.

Related tests:
- `tests/unit/test_text.py`
- `tests/integration/test_integration.py::test_text_run_writes_chunks`

## Feature F-004: Video ETL

Description:
- Probes raw videos, optionally normalizes clips with ffmpeg, merges tags, writes `video_index.parquet`.

Status:
- Implemented and tested.

Files involved:
- `src/etl/video_etl.py`, `config/dataset.yaml`.

Dependencies:
- External `ffmpeg`/`ffprobe`, `pandas`; optional `cv2` fallback path exists in code.

Acceptance criteria:
- Handles ffmpeg availability/failure, indexes videos, merges tags.

Current implementation state:
- `ffmpeg -version` passes.
- `video --dry-run --limit 2` passed with `discovered=20`, `processed=2`, `errors=0`.
- Current generated artifact has 20 video rows.

Known limitations:
- Real browser playback was not validated in this context pack.

Related tests:
- `tests/unit/test_video.py`

## Feature F-005: Incident Assembly

Description:
- Joins sensor windows, video index, and text chunks into incident rows.

Status:
- Implemented and tested.

Files involved:
- `src/etl/assemble_incidents.py`, `src/common/schemas.py`.

Dependencies:
- `pandas`, `numpy`, optional `rank-bm25` for retrieval.

Acceptance criteria:
- Assembled incidents include sensor, video, SOP, maintenance, labels, alignment, and split fields.

Current implementation state:
- Current `incidents.parquet` has 1702 rows and 21 columns.
- `assemble` completed with 1702 rows after text-retrieval caching.
- Failure labels and split distribution are now populated in the current artifact.

Known limitations:
- Failure/severity/root-cause labels are weak deterministic scaffolding, not curated ground truth.
- Regime labels remain `unknown`.

Related tests:
- `tests/unit/test_assemble.py`
- integration assembly tests in `tests/integration/test_integration.py`

## Feature F-006: Evaluation

Description:
- Computes dataset quality metrics and writes/prints PASS/WARN/FAIL grade.

Status:
- Implemented and verified.

Files involved:
- `src/evaluate.py`, `src/cli.py`.

Dependencies:
- `pandas`, project IO utilities.

Acceptance criteria:
- Evaluation command exits 0 unless grade is FAIL; metrics identify quality gaps.

Current implementation state:
- Evaluation exits 0 with grade `PASS`.

Known limitations:
- Current PASS is a demo-readiness signal over weak labels. Final semantic claims still require curated labels/provenance.

Related tests:
- `tests/integration/test_integration.py::test_eval_metrics_on_fixture`
- `tests/integration/test_integration.py::test_eval_detects_malformed_json`

## Feature F-007: Streamlit Incident Explorer

Description:
- Provides UI to inspect incident evidence: video, vibration chart, SOP text, alignment summary, raw row.

Status:
- Implemented and runtime-smoke verified.

Files involved:
- `streamlit_app.py`, `src/ui/incident_explorer.py`.

Dependencies:
- `streamlit`, `pandas`, generated Parquet artifacts.

Acceptance criteria:
- App loads and reads `data_pipeline/data_processed`.
- Incident helper functions are tested.

Current implementation state:
- HTTP smoke to `http://localhost:8501` returns 200.
- Live browser smoke verified title, incident selector, Evidence tab, Alignment tab, and Raw Row tab without visible error text.

Known limitations:
- Browser smoke test is opt-in via `RUN_BROWSER_SMOKE=1`; normal test runs skip it unless a running browser target is available.

Related tests:
- `tests/unit/test_incident_explorer.py`
- `tests/ui/test_streamlit_browser_smoke.py`

## Feature F-008: TGFX Contract Substrate

Description:
- Adds the initial TGFX spec-defined Pydantic contracts and SDD documentation substrate beside the existing Recipe A pipeline.

Status:
- Implemented for the first contract slice.

Files involved:
- `CLAUDE.md`
- `contracts/__init__.py`
- `contracts/core.py`
- `contracts/explanation.py`
- `tests/contracts/test_core_contracts.py`
- `tests/contracts/test_explanation_contracts.py`
- `docs/_sdd/*`
- `docs/_eval/*`
- `docs/_data/*`
- `docs/build_iterations/*`

Dependencies:
- `pydantic`.

Acceptance criteria:
- Contract tests pass.
- Existing Recipe A regression tests still pass.
- Contract package imports cleanly.

Current implementation state:
- `pytest tests/contracts -q`: `9 passed in 4.56s`.
- Contract tests remain included in the full suite; current requested baseline is `pytest -q --cov=src --cov=contracts --cov-report=term-missing`: `106 passed, 1 skipped`, coverage `80%`.
- Import smoke prints `SensorWindow ExplanationOutput`.

Known limitations:
- Evidence graph resolution is not implemented.
- The first fixture/meta-test eval harness now exists under Feature F-009.
- TGFX manifest/ledger/splits now exist for Recipe A artifacts; curated gold labels and evidence graph resolution are not implemented.

Related tests:
- `tests/contracts/test_core_contracts.py`
- `tests/contracts/test_explanation_contracts.py`

## Feature F-009: TGFX Fixture Evaluation Harness

Description:
- Adds a deterministic TGFX evaluation seed with fixture metrics, meta-tests, sensor verifier path, and run-ledger appends.

Status:
- Implemented for fixture/meta-test harness.

Files involved:
- `src/features/vibration.py`
- `src/eval/fixtures.py`
- `src/eval/metrics.py`
- `src/eval/verify_sensor.py`
- `src/eval/verify_llm.py`
- `src/eval/run.py`
- `tests/eval_meta/test_metrics_meta.py`
- `docs/_eval/gates.yaml`
- `docs/_eval/runs.jsonl`

Dependencies:
- `contracts`, `pydantic`, Python standard library.

Acceptance criteria:
- `pytest tests/eval_meta -x -q` passes.
- Oracle fixture prints `unsupported_claim_rate <= 0.05`.
- Corrupted interval fixture prints `iou_sensor < 0.2`.
- Run records append to `docs/_eval/runs.jsonl`.

Current implementation state:
- Eval meta-tests pass: `5 passed`.
- Full suite passes: `106 passed`, `1 skipped`, coverage `80%`.
- Fixture CLI commands produce expected oracle/corrupted metrics.

Known limitations:
- External LLM judge is not implemented; `verify_llm.py` is fixture-only.
- Real-data manifest/ledger/splits are seeded from Recipe A artifacts, but curated validation fixtures are not implemented.
- RedTeam probes and real baseline comparisons are not implemented.

Related tests:
- `tests/eval_meta/test_metrics_meta.py`

## Feature F-010: TGFX Dataset Substrate

Description:
- Generates a manifest, alignment ledger, and split ID scaffolding from current Recipe A processed artifacts.

Status:
- Implemented for Recipe A artifact substrate.

Files involved:
- `src/tgfx/dataset.py`
- `scripts/build_dataset.py`
- `docs/_data/manifest.json`
- `docs/_data/alignment_ledger.jsonl`
- `data/splits/*.jsonl`
- `tests/unit/test_tgfx_dataset.py`

Current implementation state:
- `python scripts/build_dataset.py --config config/dataset.yaml` writes 1702 ledger rows and split files for train/val/test/human_eval.

Known limitations:
- Labels are marked `weak_signal_derived_not_ground_truth`.
- Test quarantine is documented but no TGFX model/training code exists yet.
