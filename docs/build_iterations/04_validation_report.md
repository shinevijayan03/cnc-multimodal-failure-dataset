# Validation Report

| Check | Command | Result | Status |
|---|---|---|---|
| Full tests | `pytest -q --cov=src --cov=contracts --cov-report=term-missing` | `106 passed, 1 skipped`, total coverage `80%` | Pass |
| Lint | `ruff check src tests contracts scripts` | `All checks passed!` | Pass |
| Compile | `python -m compileall -q src contracts scripts streamlit_app.py` | exit code 0 | Pass |
| Text dry-run | `python -m src.cli text --config config/dataset.yaml --dry-run --limit 2` | discovered 5, processed 2, written 5, errors 0 | Pass |
| Assemble | `python -m src.cli assemble --config config/dataset.yaml` | 1702 incidents written | Pass |
| Recipe A evaluation | `python -m src.cli evaluate --config config/dataset.yaml --tier mvp` | exit code 0, grade `PASS` | Pass with weak-label caveat |
| TGFX oracle fixture | `python -m src.eval.run --fixtures oracle --no-write` | unsupported rate 0.0, IoU 1.0 | Pass |
| TGFX corrupted fixture | `python -m src.eval.run --fixtures corrupted_intervals --no-write` | IoU 0.0, wrong-time rate 1.0 | Pass |
| TGFX substrate | `python scripts/build_dataset.py --config config/dataset.yaml` | manifest 1702, ledger 1702, split files generated | Pass |
| UI HTTP smoke | `Invoke-WebRequest http://localhost:8501` | HTTP 200 | Pass |
| Live browser smoke | in-app browser | title, selector, Evidence/Alignment/Raw Row visible; no error text | Pass |

Known caveat:
- The current Recipe A `PASS` uses weak deterministic label scaffolding. It is
  demo-ready, not curated semantic ground truth.
