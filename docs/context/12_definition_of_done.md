# Definition of Done Evaluation

| Criterion | Status | Evidence | Explanation |
|---|---|---|---|
| Repository can be inspected and understood | Complete | `docs/codebase_audit/`, `docs/context/` | Audit and context docs exist |
| Dependencies install | Complete | `python -m pip install -r requirements.txt` exits 0 | Requirements already satisfied |
| CLI runs | Complete | `python -m src.cli --help` exits 0 | Commands listed |
| Application UI runs | Complete | HTTP 200 on `http://localhost:8501` | Streamlit process PID 9016 |
| Unit/integration/contract/eval-meta tests pass | Complete | `106 passed`, `1 skipped`, `80%` coverage | pytest with coverage passes |
| Lint passes | Complete | `ruff check src tests` passes | Current command output |
| Static compile passes | Complete | `compileall` exits 0 | Current command output |
| Dataset evaluation runs | Complete | `evaluate --tier mvp` exits 0 | Grade is PASS |
| Dataset semantic quality is acceptable for final claims | Partial | Label status is weak scaffolding | Curated ground-truth labels still needed |
| Fast smoke path for all ETL stages | Complete for current implementation | text dry-run completes; assemble completes | Text smoke still takes about 35s on large manuals |
| Browser-level UI validation | Partial | live browser smoke passed; opt-in test exists | Deeper interaction assertions remain optional |
| Security/dependency audit | Not Started | No tool configured | Deferred unless deployment/sharing requires it |
| Documentation matches current code | Complete for current iteration | README, context, SDD, build docs updated | Remaining caveats documented |
| Refactor readiness | Partial | checkpoint branch exists | Dirty tree still needs commit/stage decision |
| Raw data licensing/provenance verified | Unknown | No verified license manifest in current evidence | Needed before distribution |
| TGFX contract substrate | Complete | `contracts/`, `tests/contracts/`, `CLAUDE.md`, `docs/_sdd/` | First master-prompt slice implemented |
| TGFX evaluation harness | Partial | `src/eval/`, `tests/eval_meta/`, fixture CLI runs exist | Fixture/meta-test seed complete; curated real-data harness still pending |
| TGFX dataset substrate | Complete for Recipe A artifact substrate | `scripts/build_dataset.py`, `docs/_data/*`, `data/splits/*` | Curated gold labels still pending |
