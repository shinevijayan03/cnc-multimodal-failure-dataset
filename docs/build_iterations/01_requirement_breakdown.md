# Requirement Breakdown

| ID | Requirement | Acceptance Criteria | Priority | Affected Area | Test Method | Status |
|---|---|---|---:|---|---|---|
| TGFX-EVAL-001 | Implement metric functions for TGFX fixture evaluation | Metrics include schema validity, IoU, wrong-time rate, unsupported rate, attribution precision/recall, evidence recall, root-cause top-k, detection F1/AUROC, ECE | High | `src/eval/metrics.py` | `pytest tests/eval_meta -x -q` | Verified |
| TGFX-EVAL-002 | Implement deterministic fixture set | Oracle and corrupted interval fixtures are loadable and deterministic | High | `src/eval/fixtures.py` | eval meta-tests and CLI fixture runs | Verified |
| TGFX-EVAL-003 | Implement sensor verifier path importing feature functions | Sensor verifier imports `src.features.vibration` and supports fixture claims | High | `src/features/vibration.py`, `src/eval/verify_sensor.py` | eval meta-tests | Verified |
| TGFX-EVAL-004 | Implement eval CLI/run record writer | `python -m src.eval.run --fixtures ...` prints metrics and appends `docs/_eval/runs.jsonl` by default | High | `src/eval/run.py`, `docs/_eval/runs.jsonl` | fixture CLI commands | Verified |
| TGFX-EVAL-005 | Implement metric meta-tests | Oracle fixture scores as faithful, corrupted intervals lower IoU, monotonic corruption behaves correctly, reversed chain is invalid | High | `tests/eval_meta/` | `pytest tests/eval_meta -x -q` | Verified |
| TGFX-EVAL-006 | Preserve existing Recipe A behavior | Full suite, lint, compile, evaluation, and HTTP smoke pass | High | whole repo | full validation | Verified with weak-label caveat |
| TGFX-DATA-001 | Generate TGFX Recipe A artifact substrate | Manifest, alignment ledger, and split files are generated from processed artifacts | High | `src/tgfx/`, `scripts/`, `docs/_data/`, `data/splits/` | substrate CLI and unit test | Verified |
| RECIPE-A-001 | Complete pending Recipe A demo readiness tasks | Text dry-run, label/split balance, README, browser smoke, and app runtime are updated | High | ETL, UI, docs | full validation and browser smoke | Verified |

Ambiguity:
- Full external LLM judge behavior is not implemented. A deterministic fixture-only judge interface exists in `src/eval/verify_llm.py`; external judge work remains future scope.
- Current Recipe A labels are weak deterministic scaffolding, not curated semantic ground truth.
