# V&V Loop Report

## Loop VV-001: Baseline Safety

Observe:
- Repository had a dirty working tree before audit docs were created.

Diagnose:
- `git status --short` listed modified config/source/test files and untracked UI/docs/test files.

Hypothesize:
- Refactoring is unsafe until the user acknowledges or checkpoints these existing changes.

Validate:
- Commands: `git branch --show-current`, `git rev-parse HEAD`, `git status --short`.

Result:
- Branch `main`, commit `c37bea9779f7c2d8d84a03078de74aebe5c70225`, dirty state confirmed.

Fix or document:
- Documented only. No application code reverted or changed.

Re-run check:
- Not needed for baseline; adding audit docs will further dirty the tree intentionally.

Exit decision:
- Proceed with audit only; require user review before future refactor.

Status:
- Open risk, documented.

## Loop VV-002: Environment Setup

Observe:
- README instructs `python -m pip install -r requirements.txt`.

Diagnose:
- Need to confirm dependencies in the active Python environment.

Hypothesize:
- Existing Anaconda/user-site environment already has dependencies.

Validate:
- Command: `python -m pip install -r requirements.txt`.

Result:
- Exit code 0; requirements already satisfied. Pip noted normal site-packages is not writeable and used user installation.

Fix or document:
- No fix needed.

Re-run check:
- `python -m src.cli --help` passed.

Exit decision:
- Environment is usable for audit.

Status:
- Closed.

## Loop VV-003: External Video Tool Availability

Observe:
- Video ETL requires ffmpeg/ffprobe according to README, requirements note, and `src/etl/video_etl.py`.

Diagnose:
- If ffmpeg is absent, video behavior degrades or skips.

Hypothesize:
- ffmpeg is installed on PATH.

Validate:
- Command: `ffmpeg -version`.

Result:
- Exit code 0; `ffmpeg version 8.1.1-full_build-www.gyan.dev`.

Fix or document:
- No fix needed.

Re-run check:
- `python -m src.cli video --config config/dataset.yaml --dry-run --limit 2` passed.

Exit decision:
- External video tool dependency is satisfied locally.

Status:
- Closed.

## Loop VV-004: Application Execution

Observe:
- User asked to execute the application so it can be tested.

Diagnose:
- Need to verify local web server, not just process creation.

Hypothesize:
- Streamlit app runs from `streamlit_app.py` and reads existing processed artifacts.

Validate:
- Observed process PID `9016` running `python -m streamlit run streamlit_app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false`.
- Command: `Invoke-WebRequest -Uri http://localhost:8501 -UseBasicParsing -TimeoutSec 15`.

Result:
- HTTP status 200; content length 1522.

Fix or document:
- No fix needed.

Re-run check:
- Rechecked TCP connection on port 8501 and HTTP status.

Exit decision:
- App execution verified.

Status:
- Closed.

## Loop VV-005: Test and Lint Baseline

Observe:
- CI and README expect pytest and ruff.

Diagnose:
- Need to validate current local baseline before refactor readiness.

Hypothesize:
- Test and lint baseline is green.

Validate:
- `pytest --collect-only -q`.
- `pytest -q --cov=src --cov-report=term-missing`.
- `ruff check src tests`.
- `python -m compileall -q src streamlit_app.py`.

Result:
- 87 tests collected.
- 87 tests passed; coverage 82%.
- Ruff passed.
- Compileall passed.

Fix or document:
- No fix needed.

Re-run check:
- Not required after passing checks.

Exit decision:
- Quality gate is green.

Status:
- Closed.

## Loop VV-006: Dataset Evaluation Warnings

Observe:
- Evaluation exits 0 but grade is `WARN`.

Diagnose:
- Need to decide whether warning is runtime failure or data-readiness issue.

Hypothesize:
- The warning is caused by semantic label quality, not broken files.

Validate:
- Command: `python -m src.cli evaluate --config config/dataset.yaml --tier mvp`.

Result:
- `pct_missing_sensor_file=0.0`, `pct_missing_video_file=0.0`, `pct_dangling_chunk_id=0.0`.
- Warnings: dominant class share 1.0, unknown failure 1.0, entropy 0.0.

Fix or document:
- Documented as data-quality/readiness risk; no data curation performed.

Re-run check:
- Not applicable until labels are curated.

Exit decision:
- App is runnable; dataset is not semantically ready for final claims.

Status:
- Open risk, documented.

## Loop VV-007: Pipeline Dry-Run Timeout

Observe:
- `python -m src.cli all --config config/dataset.yaml --dry-run --limit 2` timed out after 124 seconds.

Diagnose:
- Need to isolate stage.

Hypothesize:
- A heavy stage in `all` ignores or delays the limit boundary enough to exceed a smoke-test timeout.

Validate:
- Ran individual stage dry-runs with `--limit 2`.

Result:
- Sensor passed in under timeout.
- Video passed in under timeout.
- Assemble passed in under timeout.
- Text timed out after 64 seconds and left a process running.

Fix or document:
- Stopped orphan text process PID `38176`.
- Documented root risk. No code fix attempted because prompt forbids refactoring.

Re-run check:
- Verified only Streamlit python process remained.

Exit decision:
- Treat text ETL dry-run performance as a refactor-readiness risk, not a blocker for UI testing because processed artifacts exist.

Status:
- Open risk, documented.

Revalidation:
- On 2026-07-02 20:06 Asia/Calcutta, the stage isolation was repeated.
- `sensor --dry-run --limit 2`, `video --dry-run --limit 2`, and `assemble --dry-run --limit 2` passed.
- `text --dry-run --limit 2` timed out after 64 seconds again.
- The orphan Python process PID `37436` was stopped.
- Exit decision remains unchanged: open risk, not a blocker for current UI testing, but a blocker for confident text ETL refactoring without profiling.
