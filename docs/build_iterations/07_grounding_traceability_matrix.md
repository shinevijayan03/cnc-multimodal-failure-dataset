# Grounding Traceability Matrix

| Requirement ID | User Spec Evidence | Code Evidence | Test Evidence | Runtime Evidence | Status | Confidence |
|---|---|---|---|---|---|---|
| TGFX-EVAL-001 | master prompt §6.1-§6.6 | `src/eval/metrics.py` | `tests/eval_meta/test_metrics_meta.py` | fixture CLI metrics | Verified | High |
| TGFX-EVAL-002 | master prompt §6.7 oracle/corruption fixtures | `src/eval/fixtures.py` | eval meta-tests | `--fixtures oracle`, `--fixtures corrupted_intervals` | Verified | High |
| TGFX-EVAL-003 | master prompt §6.4a and constitution I-3 | `src/features/vibration.py`, `src/eval/verify_sensor.py` | eval meta-tests | fixture CLI | Verified | High |
| TGFX-EVAL-004 | master prompt §2 runs.jsonl schema and §11.2 entrypoint | `src/eval/run.py`, `docs/_eval/runs.jsonl` | eval meta-tests plus CLI | run records appended | Verified | High |
| TGFX-EVAL-005 | master prompt §6.7 meta-tests | `tests/eval_meta/test_metrics_meta.py` | `pytest tests/eval_meta -x -q` | N/A | Verified | High |
| TGFX-EVAL-006 | master prompt preservation rules | Recipe A modules preserved with targeted bounded-smoke/weak-label changes | full pytest, ruff, compileall | HTTP 200, Recipe A eval PASS | Verified with weak-label caveat | High |
| TGFX-DATA-001 | master prompt T-02/T-03 | `src/tgfx/dataset.py`, `scripts/build_dataset.py`, `docs/_data/*`, `data/splits/*` | `tests/unit/test_tgfx_dataset.py` | substrate command generated 1702 ledger rows | Verified for Recipe A artifact substrate | High |
| RECIPE-A-001 | user pending task list | `src/etl/text_etl.py`, `src/etl/assemble_incidents.py`, `config/dataset.yaml`, `README.md`, `tests/ui/` | full pytest and browser smoke | eval PASS, app visible | Verified with weak-label caveat | High |
