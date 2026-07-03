# Next Iteration Handoff

## Current Goal

Prepare curated TGFX validation fixtures and evidence graph resolution before
any model/encoder/fusion/decoder work.

## Completed Work

- App is running and reachable at `http://localhost:8501`.
- Checkpoint branch created: `codex/complete-pending-phases`.
- Codebase audit artifacts exist under `docs/codebase_audit/`.
- Context compaction artifacts exist under `docs/context/`.
- TGFX contract substrate exists: `CLAUDE.md`, `contracts/`, `tests/contracts/`, `docs/_sdd/`, `docs/_eval/`, `docs/_data/`, `docs/build_iterations/`.
- TGFX fixture eval harness exists under `src/eval/`, `src/features/vibration.py`, and `tests/eval_meta/`.
- Text dry-run is bounded and completes for the current staged manuals.
- Current `incidents.parquet` has populated weak failure/severity/root-cause labels and train/val/test/human_eval split diversity.
- Recipe A MVP evaluation exits 0 with grade `PASS`.
- Browser-level smoke coverage exists as an opt-in test, and live browser smoke passed.
- TGFX T-02/T-03 Recipe A artifact substrate exists: `src/tgfx/dataset.py`, `scripts/build_dataset.py`, `docs/_data/manifest.json`, `docs/_data/alignment_ledger.jsonl`, and `data/splits/*.jsonl`.
- Current validation: 106 tests pass, 1 opt-in browser smoke skipped, 80% coverage, ruff passes, compileall passes.

## Remaining Work

1. Commit/stage or otherwise checkpoint the dirty branch after user review.
2. Curate real semantic labels/provenance before final thesis-quality label claims.
3. Harden TGFX curated validation fixtures and evidence graph resolution.
4. Add RedTeam probes and real baseline comparisons.
5. Add security/dependency and package-build validation if distribution is planned.

## Known Blockers

- Dirty working tree still needs a commit/stage decision.
- Weak labels are not curated ground truth.
- Raw data licensing/provenance remains Unknown for distribution.

## Files Most Likely To Change

For curated labels/provenance:
- `src/etl/assemble_incidents.py`
- `src/evaluate.py`
- `config/dataset.yaml`
- `docs/_data/manifest.json`
- tests for assembly/evaluation

For TGFX evidence graph / curated validation:
- `contracts/`
- `src/tgfx/`
- `src/eval/`
- `docs/_eval/gates.yaml`
- `docs/_data/alignment_ledger.jsonl`
- new tests under `tests/`

For UI deep browser validation:
- `tests/ui/test_streamlit_browser_smoke.py`
- `streamlit_app.py`
- `src/ui/incident_explorer.py`

## Recommended Order Of Implementation

1. Review and commit/stage the current branch.
2. Re-run baseline commands.
3. Pick one objective: curated labels/provenance or TGFX evidence graph.
4. Add targeted guardrail tests.
5. Apply minimal code/doc changes.
6. Re-run targeted tests.
7. Re-run full validation.
8. Update `docs/context/`.

## Recommended Validation Strategy

Always run:
- `pytest -q --cov=src --cov=contracts --cov-report=term-missing`
- `ruff check src tests contracts scripts`
- `python -m compileall -q src contracts scripts streamlit_app.py`
- `python -m src.cli evaluate --config config/dataset.yaml --tier mvp`
- HTTP smoke for UI changes.

For TGFX dataset substrate:
- `python scripts/build_dataset.py --config config/dataset.yaml`
- verify `docs/_data/manifest.json`
- verify `docs/_data/alignment_ledger.jsonl`
- verify `data/splits/*.jsonl`

For UI work:
- live browser smoke.
- optional: `RUN_BROWSER_SMOKE=1 pytest tests/ui -q` when Playwright and a running Streamlit server are available.

## Potential Risks

- Weak labels may be mistaken for curated semantic ground truth.
- Refactor may change Parquet schemas unintentionally.
- Text ETL dry-run still takes tens of seconds on large PDFs.
- Untracked files may be lost or mixed without a commit/stage checkpoint.

## Rollback Considerations

- Before further edits, record `git status --short`.
- Use small patches.
- Do not revert unrelated user changes.
- If rollback is needed, revert only files changed in the current iteration.

## Estimated Complexity

- Documentation-only update: Low.
- Deep UI browser interaction test: Medium.
- Text ETL further performance hardening: Medium.
- Dataset semantic label curation: High because it requires provenance and domain review.
- TGFX evidence graph / curated validation fixtures: High.
