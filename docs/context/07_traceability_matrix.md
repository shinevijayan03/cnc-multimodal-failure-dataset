# Traceability Matrix

| Requirement | Design | Implementation | Test | Runtime Validation | Status |
|---|---|---|---|---|---|
| REQ-CLI-001 CLI orchestration | ADR-001 | `src/cli.py` | CLI tests in `tests/integration/test_integration.py` | `python -m src.cli --help` | Complete |
| REQ-SENS-001 Sensor windows | Local Parquet contracts, config-driven ETL | `src/etl/sensor_etl.py`, `src/common/schemas.py` | `tests/unit/test_sensor.py`, sensor integration tests | `sensor --dry-run --limit 2` passed; artifact 1702 rows | Complete |
| REQ-TEXT-001 Text chunks | Local Parquet contracts, optional tokenizer/doc readers | `src/etl/text_etl.py` | `tests/unit/test_text.py`, `test_text_run_writes_chunks` | artifact 934 rows; bounded dry-run completes | Complete |
| REQ-VID-001 Video index | ffmpeg external binary, local video index | `src/etl/video_etl.py` | `tests/unit/test_video.py` | `video --dry-run --limit 2` passed; artifact 20 rows | Complete |
| REQ-ASM-001 Incident assembly | Multimodal linking into incident contract | `src/etl/assemble_incidents.py`, `src/common/schemas.py` | `tests/unit/test_assemble.py`, assembly integration tests | `incidents.parquet` 1702 rows; failure/split diversity populated | Complete with weak-label caveat |
| REQ-EVAL-001 Dataset evaluation | MetricsReport and grade thresholds | `src/evaluate.py`, `src/cli.py` | evaluation integration tests | `evaluate --tier mvp` grade PASS | Complete |
| REQ-UI-001 Incident explorer | Thin Streamlit UI with helper module | `streamlit_app.py`, `src/ui/incident_explorer.py` | `tests/unit/test_incident_explorer.py`, `tests/ui/test_streamlit_browser_smoke.py` | HTTP 200 and live browser smoke | Complete for smoke coverage |
| REQ-DATA-001 Semantic label quality | Evaluation thresholds expose quality | `src/etl/assemble_incidents.py`, `src/evaluate.py`, current artifacts | evaluation tests check metric machinery; weak-label unit tests | current grade PASS, labels are weak deterministic scaffolding | Partial |
| REQ-DOC-001 Current docs | Audit/context docs | `README.md`, `docs/codebase_audit/`, `docs/context/` | File-presence checks | final required-file check | Complete for current iteration |
| REQ-SAFE-001 Checkpoint dirty tree | Git safety discipline | branch `codex/complete-pending-phases` | no automated test | `git status --short` dirty on checkpoint branch | Partial |
| REQ-SEC-001 Security baseline | Deferred hardening | none configured | none configured | source scan only | Open |
| REQ-TGFX-001 TGFX contract substrate | Master prompt sections 0-3 and 12 | `CLAUDE.md`, `contracts/`, `docs/_sdd/` | `tests/contracts/`, `pytest tests/contracts -q` | import smoke | Complete |
| REQ-TGFX-002 TGFX eval harness | Master prompt §6 and §11.2 | `src/eval/`, `src/features/vibration.py`, `docs/_eval/gates.yaml` | `tests/eval_meta/`, `pytest tests/eval_meta -x -q` | `python -m src.eval.run --fixtures oracle`; corrupted fixture run | Complete for fixture/meta-test seed |
| REQ-TGFX-003 TGFX dataset substrate | Master prompt §5 and §12 | `src/tgfx/dataset.py`, `scripts/build_dataset.py`, `docs/_data/*`, `data/splits/*` | `tests/unit/test_tgfx_dataset.py` | `python scripts/build_dataset.py --config config/dataset.yaml` | Complete for Recipe A artifact substrate |

Implementation-to-test map:
- `src/cli.py` -> integration CLI tests.
- `src/common/config.py` -> `tests/unit/test_config.py`.
- `src/common/schemas.py` -> `tests/unit/test_schemas.py`.
- `src/common/io_utils.py` and `src/common/ids.py` -> `tests/unit/test_io_ids.py`.
- `src/etl/sensor_etl.py` -> `tests/unit/test_sensor.py` and integration sensor tests.
- `src/etl/text_etl.py` -> `tests/unit/test_text.py` and integration text tests.
- `src/etl/video_etl.py` -> `tests/unit/test_video.py`.
- `src/etl/assemble_incidents.py` -> `tests/unit/test_assemble.py` and integration assembly tests.
- `src/evaluate.py` -> integration evaluation tests.
- `src/ui/incident_explorer.py` -> `tests/unit/test_incident_explorer.py`.
- `streamlit_app.py` -> no direct browser test; covered indirectly by import/compile and UI helper tests. Status: Partial.
- `contracts/core.py` and `contracts/explanation.py` -> `tests/contracts/test_core_contracts.py` and `tests/contracts/test_explanation_contracts.py`.
- `src/eval/metrics.py`, `src/eval/fixtures.py`, `src/eval/verify_sensor.py`, `src/features/vibration.py` -> `tests/eval_meta/test_metrics_meta.py`.
- `src/tgfx/dataset.py`, `scripts/build_dataset.py` -> `tests/unit/test_tgfx_dataset.py`.
- `tests/ui/test_streamlit_browser_smoke.py` -> opt-in browser smoke with `RUN_BROWSER_SMOKE=1`; live browser smoke also verified manually through automation.
