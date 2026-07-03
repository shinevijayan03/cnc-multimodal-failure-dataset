# Next Prompt For Refactoring

Use this prompt in a later Codex session when ready to begin refactoring.

```text
Act as a senior software architect, QA lead, and refactoring engineer for this repository:

E:\1.Final-Year-Project-2026\4. demo-old\cnc-multimodal-failure-dataset

Ground yourself first in the audit artifacts under:

docs/codebase_audit/

Current verified context:
- This is a Python Recipe A CNC multimodal dataset pipeline.
- Main CLI entry point: python -m src.cli.
- Main UI entry point: streamlit_app.py.
- Main generated artifacts: data_pipeline/data_processed/incidents.parquet, sensor_windows.parquet, text_chunks.parquet, video_index.parquet.
- Current verified app status from audit: Streamlit responded on http://localhost:8501 with HTTP 200.
- Current verified quality status from audit: pytest passed 87 tests with 82% total coverage; ruff passed; compileall passed.
- Current verified data quality status from audit: evaluation grade WARN because failure/regime labels are mostly unknown and class diversity is weak.
- Current verified runtime risk from audit: text ETL dry-run with --limit 2 timed out; all dry-run timed out because of the text stage.

Refactor objective:
[USER MUST FILL IN ONE OBJECTIVE, for example: improve Streamlit UI maintainability, optimize text ETL dry-run performance, clean module boundaries, or update docs.]

Safety rules:
1. Do not start broad rewrites.
2. Do not change raw data.
3. Do not change Parquet schema contracts unless explicitly approved.
4. Do not change ID generation, split assignment, label semantics, or evaluation thresholds unless they are the explicit target.
5. Preserve user changes in the dirty working tree.
6. Ground every claim in files, tests, commands, or runtime behavior.
7. Mark inferences and unknowns explicitly.
8. Keep changes small and reversible.

Required ETVX structure:

Phase R0: Baseline and Scope
- Entry Criteria: audit artifacts exist; user selected objective.
- Task: inspect git status, branch, commit, relevant files, and prior audit risks.
- Validation and Verification: run git status, read relevant audit docs, identify affected tests.
- Exit Criteria: exact refactor scope and non-goals documented.

Phase R1: Guardrail Tests
- Entry Criteria: scope agreed.
- Task: add or identify tests that protect the selected boundary.
- Validation and Verification: run pytest collection and targeted tests.
- Exit Criteria: guardrail tests pass or expected failures are documented before code changes.

Phase R2: Minimal Refactor
- Entry Criteria: guardrails exist.
- Task: apply the smallest code changes needed for the selected objective.
- Validation and Verification: run targeted tests after each meaningful edit.
- Exit Criteria: behavior preserved unless explicitly changed.

Phase R3: Full Verification
- Entry Criteria: targeted changes complete.
- Task: run full verification.
- Required commands:
  - pytest -q --cov=src --cov-report=term-missing
  - ruff check src tests
  - python -m compileall -q src streamlit_app.py
  - python -m src.cli evaluate --config config/dataset.yaml --tier mvp
  - Streamlit HTTP smoke check if UI is affected
- Exit Criteria: results recorded; failures fixed or documented.

Phase R4: Readiness Report
- Entry Criteria: verification complete.
- Task: summarize changed files, tests, risks, and rollback plan.
- Exit Criteria: user can review and decide whether to approve the next phase.

V&V loop requirement:
For every issue encountered, use:
1. Observe
2. Diagnose
3. Hypothesize
4. Validate
5. Fix or document
6. Re-run check
7. Decide exit or continue

Rollback plan:
- Before edits, record git status and affected files.
- Use apply_patch or minimal scoped edits only.
- Do not revert unrelated user changes.
- If a refactor fails, revert only the refactor changes made in this session, preserving prior user changes.
- Keep a list of changed files and exact validation commands.

Exit response must include:
1. Objective completed or blocked
2. Files changed
3. Tests and command results
4. Behavioral changes
5. Remaining risks
6. Recommended next step
```

