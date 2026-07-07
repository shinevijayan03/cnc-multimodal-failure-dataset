# Loop History

This file records durable engineering loops only.

## LOOP-001: Application Runtime Enablement

Goal:
- Execute the app so it can be tested.

Problem:
- Need to confirm whether the UI can run against existing processed artifacts.

Root cause:
- Not an error; runtime state needed verification.

Fix:
- Started/kept Streamlit on port 8501 with `python -m streamlit run streamlit_app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false`.

Verification:
- `Invoke-WebRequest http://localhost:8501` returned HTTP 200.
- Process PID `9016` is listening on port 8501.

Final outcome:
- App is available for local testing.

## LOOP-002: Codebase Audit and Readiness Baseline

Goal:
- Produce evidence-backed audit artifacts before refactoring.

Problem:
- Need a repository-grounded basis for future work.

Root cause:
- No single current audit pack existed before `docs/codebase_audit/`.

Fix:
- Created 12 audit files under `docs/codebase_audit/`.

Verification:
- File-presence check confirmed all 12 files.
- Current validation commands pass except known text dry-run timeout.

Final outcome:
- Refactor readiness classified as `READY WITH RISKS`.

## LOOP-003: Text ETL Dry-Run Timeout Isolation

Goal:
- Determine why `all --dry-run --limit 2` is not a fast smoke command.

Problem:
- `python -m src.cli all --config config/dataset.yaml --dry-run --limit 2` timed out.

Root cause:
- Confirmed stage-level symptom: `text --dry-run --limit 2` times out. Deeper root cause is not verified. Inference: heavy PDF/manual parsing or tokenization.

Fix:
- No business logic fix applied. Orphan Python processes from timed-out text dry-runs were stopped.

Verification:
- `sensor`, `video`, and `assemble` dry-runs passed.
- `text` dry-run timed out again on revalidation.

Final outcome:
- Open issue and refactor risk documented.

## LOOP-004: Context Compaction Pack

Goal:
- Create durable project memory under `docs/context/`.

Problem:
- Future Codex sessions should continue without reading prior conversation.

Root cause:
- Conversation context is transient; repository context must be file-backed.

Fix:
- Created the required `docs/context/*.md` files grounded in current source, audit docs, commands, and generated artifacts.

Verification:
- Required-file checks must pass before final response.

Final outcome:
- Context pack ready after final verification.

## LOOP-005: TGFX Contract Substrate

Goal:
- Start the master-prompt TGFX build with the contract-first slice and preserve the existing Recipe A app.

Problem:
- The master prompt specifies a new TGFX SDD substrate while the repo already contains a working Recipe A pipeline.

Root cause:
- Existing implementation and new target architecture differ; replacing current schemas would be a broad rewrite.

Fix:
- Added TGFX contracts in a new `contracts` package, added `CLAUDE.md`, `docs/_sdd/`, placeholder eval/data substrate, and build-iteration logs.

Verification:
- `pytest tests/contracts -q`: 9 passed.
- Full regression: 96 passed with 83% coverage.
- RUFF, compileall, evaluation, import smoke, and Streamlit HTTP smoke passed.

Final outcome:
- First TGFX substrate iteration was DONE WITH KNOWN RISKS; this was superseded by LOOP-006, which added the fixture evaluation harness.

## LOOP-006: TGFX Fixture Evaluation Harness

Goal:
- Implement T-04..T-06 before any TGFX model code.

Problem:
- `src/eval/`, `tests/eval_meta/`, and `src/features/` were absent.

Root cause:
- Previous iteration only created contracts and placeholders.

Fix:
- Added deterministic fixture harness, metric functions, sensor verifier, fixture-only judge interface, run CLI, single feature path seed, eval meta-tests, gate definitions, and run ledger records.

Verification:
- `pytest tests/eval_meta -x -q`: 5 passed.
- `python -m src.eval.run --fixtures oracle`: unsupported rate 0.0, IoU 1.0.
- `python -m src.eval.run --fixtures corrupted_intervals`: IoU 0.0, wrong-time rate 1.0.
- Full regression: 101 passed; ruff, compileall, Recipe A evaluation, and HTTP smoke passed.

Final outcome:
- T-04..T-06 complete for fixture/meta-test harness. Next TGFX task should build dataset substrate T-02/T-03 or harden eval against real validation fixtures.

## LOOP-007: Context Drift Verification

Goal:
- Verify repository state against `docs/context/` before the next implementation objective.

Problem:
- Most runtime claims matched current behavior, but a few context statements still referenced older test counts or pre-TGFX eval-harness limitations.

Root cause:
- Context docs had been updated across staged iterations; some earlier-count references remained after the T-04..T-06 harness landed.

Fix:
- Updated current-state documentation in `docs/context/00_project_state.md`, `02_current_features.md`, `03_open_requirements.md`, `05_known_issues.md`, `06_validation_status.md`, and `12_definition_of_done.md`.

Verification:
- `pytest -q --cov=src --cov-report=term-missing`: 101 passed, 80% coverage.
- `ruff check src tests`: passed.
- `python -m compileall -q src streamlit_app.py`: passed.
- `python -m src.cli evaluate --config config/dataset.yaml --tier mvp`: exited 0 with grade WARN.
- HTTP smoke to `http://localhost:8501`: HTTP 200.

Final outcome:
- Implementation matches the main context baseline. Remaining drift is intentional README baseline drift, plus historical loop records that preserve prior iteration results.

## LOOP-008: Pending Task Completion Pass

Goal:
- Complete the requested pending tasks in phases and leave the application running.

Problem:
- The repo still had README drift, text dry-run timeout, weak label/split diversity, missing browser smoke coverage, and TGFX T-02/T-03 placeholders.

Root cause:
- Earlier iterations focused on audit, contracts, and fixture eval harness; downstream substrate and demo artifact quality were deferred.

Fix:
- Created branch `codex/complete-pending-phases`.
- Added bounded dry-run PDF page cap.
- Added deterministic weak label scaffolding and incident-id split grouping.
- Cached repeated text retrieval during assembly.
- Added opt-in browser smoke test and performed live browser smoke.
- Added `src/tgfx/dataset.py`, `scripts/build_dataset.py`, manifest, ledger, and split scaffolding.
- Updated README, SDD, build-iteration, and context docs.

Verification:
- `pytest -q --cov=src --cov=contracts --cov-report=term-missing`: 106 passed, 1 skipped, 80% coverage.
- `ruff check src tests contracts scripts`: passed.
- `python -m compileall -q src contracts scripts streamlit_app.py`: passed.
- `python -m src.cli text --config config/dataset.yaml --dry-run --limit 2`: completed.
- `python -m src.cli assemble --config config/dataset.yaml`: completed with 1702 incidents.
- `python -m src.cli evaluate --config config/dataset.yaml --tier mvp`: grade PASS.
- `python scripts/build_dataset.py --config config/dataset.yaml`: manifest 1702, ledger 1702, split files generated.
- Browser smoke: title, selector, tabs visible; no error text.

Final outcome:
- Final running demo application is available at `http://localhost:8501`. Remaining high-signal caveat: labels are weak deterministic scaffolding, not curated ground truth.
