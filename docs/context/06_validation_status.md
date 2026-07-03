# Validation Status

Date: 2026-07-02
Environment: Windows PowerShell, Python 3.12.7 from Anaconda path evidence in process/test output.

| Area | Command | Result | Pass/Fail | Evidence | Date |
|---|---|---|---|---|---|
| Dependency install | `python -m pip install -r requirements.txt` | Requirements already satisfied | Pass | command output; `docs/codebase_audit/00_execution_log.md` | 2026-07-02 |
| CLI smoke | `python -m src.cli --help` | Commands listed | Pass | current command output | 2026-07-02 |
| Unit/integration/contract/eval-meta tests | `pytest -q --cov=src --cov=contracts --cov-report=term-missing` | `106 passed, 1 skipped in 75.30s` | Pass | current command output | 2026-07-02 |
| Coverage | `pytest -q --cov=src --cov=contracts --cov-report=term-missing` | Total coverage `80%` | Pass | current command output | 2026-07-02 |
| Lint | `ruff check src tests` | `All checks passed!` | Pass | current command output | 2026-07-02 |
| Lint including contracts | `ruff check src tests contracts` | `All checks passed!` | Pass | current command output | 2026-07-02 |
| Static compile | `python -m compileall -q src contracts scripts streamlit_app.py` | exit code 0 | Pass | current command output | 2026-07-02 |
| Runtime HTTP smoke | `Invoke-WebRequest http://localhost:8501` | `HTTP_STATUS=200`, `CONTENT_LENGTH=1522` | Pass | current command output | 2026-07-02 |
| Evaluation | `python -m src.cli evaluate --config config/dataset.yaml --tier mvp` | exit code 0, grade `PASS` | Pass with weak-label caveat | current command output | 2026-07-02 |
| Sensor dry-run | `python -m src.cli sensor --config config/dataset.yaml --dry-run --limit 2` | processed 2, errors 0 | Pass | `docs/codebase_audit/00_execution_log.md` | 2026-07-02 |
| Video dry-run | `python -m src.cli video --config config/dataset.yaml --dry-run --limit 2` | processed 2, errors 0 | Pass | `docs/codebase_audit/00_execution_log.md` | 2026-07-02 |
| Assemble dry-run | `python -m src.cli assemble --config config/dataset.yaml --dry-run --limit 2` | processed 2, errors 0 | Pass | `docs/codebase_audit/00_execution_log.md` | 2026-07-02 |
| Text dry-run | `python -m src.cli text --config config/dataset.yaml --dry-run --limit 2` | completed: discovered 5, processed 2, written 5, errors 0 | Pass | current command output | 2026-07-02 |
| TGFX dataset substrate | `python scripts/build_dataset.py --config config/dataset.yaml` | manifest 1702, ledger 1702, split files train/val/test/human_eval | Pass | current command output and generated artifacts | 2026-07-02 |
| TGFX contract tests | `pytest tests/contracts -q` | `9 passed in 4.56s` | Pass | current command output | 2026-07-02 |
| TGFX eval meta-tests | `pytest tests/eval_meta -x -q` | `5 passed in 8.80s` | Pass | current command output | 2026-07-02 |
| TGFX oracle fixture eval | `python -m src.eval.run --fixtures oracle` | `unsupported_claim_rate=0.0`, `iou_sensor=1.0` | Pass | current command output and `docs/_eval/runs.jsonl` | 2026-07-02 |
| TGFX corrupted interval eval | `python -m src.eval.run --fixtures corrupted_intervals` | `iou_sensor=0.0`, `wrong_time_claim_rate=1.0` | Pass | current command output and `docs/_eval/runs.jsonl` | 2026-07-02 |
| Browser UI smoke | in-app browser to `http://localhost:8501` | title, incident selector, Evidence/Alignment/Raw Row visible; no error text | Pass | browser automation output | 2026-07-02 |
| Regression baseline | Full test + lint + compile + runtime smoke | Green with weak-label caveat | Pass | current commands and audit docs | 2026-07-02 |

Unknown:
- Deep browser interaction validation is Unknown; only smoke-level browser validation is verified.
- Package wheel build validation is Unknown; no native build command is part of CI.
