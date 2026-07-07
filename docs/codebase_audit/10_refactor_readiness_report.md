# Refactor Readiness Report

## Decision

READY WITH RISKS

Revalidated on 2026-07-02 20:06 Asia/Calcutta. The decision remains unchanged.

## Why

The codebase is runnable and has a strong automated baseline:
- Streamlit app responds on `http://localhost:8501` with HTTP 200.
- CLI help works.
- Dataset evaluation runs and exits 0.
- 87 tests pass with 82% total coverage.
- Ruff lint passes.
- Python compileall passes.
- Dependencies are installed and ffmpeg is available.

The risks are significant but bounded:
- The working tree was dirty before this audit.
- `text --dry-run --limit 2` times out and can leave a process running.
- Dataset semantic labels are weak: `pct_unknown_failure=1.0`, `dominant_class_share=1.0`, and `entropy_failure=0.0`.
- Full browser interaction testing was not performed.

## What Is Safe To Refactor Next

Safe candidates:
- Documentation freshness fixes, especially README test count and coverage.
- Non-behavioral module organization if tests remain green.
- UI helper refactors inside `src/ui/incident_explorer.py` with existing tests expanded first.
- Config documentation cleanup.
- Test harness improvements and additional smoke tests.
- Text ETL profiling instrumentation that does not alter output semantics.

## What Must Not Be Touched Yet

Do not broadly rewrite these until contracts and golden outputs are captured:
- Parquet schema fields in `SensorWindowRow`, `TextChunkRow`, `VideoIndexRow`, `IncidentRow`.
- ID generation in `src/common/ids.py`.
- Split assignment behavior in `src/etl/assemble_incidents.py`.
- Label derivation and evaluation thresholds, unless the refactor objective is explicitly data quality.
- Raw data folder contents, unless the user explicitly approves curation.

## What Requires User Clarification

1. Whether the dirty working tree should be committed, branched, or treated as disposable.
2. Whether the next refactor target is UI polish, ETL performance, architecture cleanup, or data quality.
3. Whether raw data and generated processed artifacts should be versioned, ignored, or regenerated.
4. Whether final thesis goals prioritize demo usability or real-data semantic labeling.

## What Needs More Tests Before Changing

| Area | Needed Test |
|---|---|
| Streamlit UI | Browser smoke test that loads app, selects incidents, checks no visible error |
| Text ETL | Performance smoke test with representative PDF/manual fixture |
| Artifact contracts | Golden schema/column tests for all Parquet outputs |
| CLI all path | Fast dry-run or smoke mode that completes inside a bounded time |
| Packaging | Optional wheel/console-script smoke if distribution matters |

## Recommended Next Refactoring Phases

### Phase R0: Checkpoint and Scope
- User reviews current dirty state.
- Create a branch or commit checkpoint before refactor.
- Select one refactor objective.

### Phase R1: Test Guardrails
- Add UI smoke test or documented manual smoke script.
- Add artifact contract tests.
- Add text ETL performance regression check.

### Phase R2: Low-Risk Documentation and Runtime Hygiene
- Update README status.
- Document verified commands and known warnings.
- Improve log clarity around long-running text ETL.

### Phase R3: Targeted Refactor
- Refactor one boundary at a time.
- Run `pytest -q --cov=src --cov-report=term-missing`, `ruff check src tests`, `python -m compileall -q src streamlit_app.py`, and Streamlit HTTP smoke after each boundary.

### Phase R4: Data Quality Work
- Only after refactor guardrails are stable, address unknown failure/regime labels and split diversity.

## Go/No-Go

Go for scoped refactoring after user review of the dirty working tree and target selection.

No-go for broad rewrites, schema changes, or data curation without explicit approval.
