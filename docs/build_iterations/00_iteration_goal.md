# Iteration Goal

## Objective

Complete the requested pending tasks in phases and leave a final running demo
application with Recipe A and TGFX substrate aligned.

## Scope

Implemented:
- checkpoint branch `codex/complete-pending-phases`
- bounded text ETL dry-run page cap
- weak deterministic label scaffolding and split diversity
- assembly text-retrieval cache
- opt-in browser-level Streamlit smoke test
- TGFX T-02/T-03 Recipe A artifact substrate
- README, SDD, context, and build-iteration updates

## Non-Scope

- No raw data edits.
- No Parquet schema changes.
- No model, encoder, VLM, fusion, decoder, or external LLM judge code.
- No claim that weak labels are curated semantic ground truth.

## ETVX

Entry Criteria:
- Context docs and prior validation baseline exist.
- Dirty tree must be isolated before refactoring.
- Existing Recipe A behavior must be preserved.

Task:
- Complete pending tasks with small guardrailed changes.

Validation and Verification:
- Full pytest with coverage.
- Ruff.
- Compileall.
- Recipe A evaluation.
- Text dry-run.
- TGFX fixture eval.
- TGFX substrate generation.
- HTTP and live browser smoke.

Exit Criteria:
- Application runs at `http://localhost:8501`.
- Evaluation exits 0.
- TGFX manifest/ledger/splits are generated.
- Docs record remaining weak-label caveat and next objective.
