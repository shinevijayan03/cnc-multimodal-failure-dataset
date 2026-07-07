# 03 — Validation Strategy

## Layers of validation (every phase)

1. **Contract tests** (`tests/contracts/`) — every new producer must emit
   pydantic-valid contract instances; schema violations fail the branch (I-2, I-10).
2. **Focused unit tests** — synthetic-input tests for each new numeric
   component (mirrors existing style: EventDetector tested with synthetic
   signals). Determinism asserted with fixed seeds (I-5).
3. **Meta-tests** — for metric or verifier changes: corrupted-input fixtures
   must degrade scores (existing pattern in `tests/eval_meta/`); required
   re-run whenever `src/eval/` changes (I-6).
4. **Full suite** — `pytest -q` must stay green; no phase may exit with a
   failing or newly-skipped test (except documented opt-in markers).
5. **Static checks** — `ruff check src tests contracts scripts`;
   `python -m compileall`.
6. **Runtime smoke** — the app must start at the end of every phase:
   `python -m src.cli evaluate --tier mvp` (grade PASS) and Streamlit
   headless healthz probe (procedure in
   `docs/architecture_audit/08_runtime_execution_report.md` §5).
7. **Run records** — any produced metric appends to `docs/_eval/runs.jsonl`
   with git_sha/config_hash/seed/dataset_manifest_hash. A metric without a
   run record does not exist (I-5/I-7).
8. **Ratchet check** — before merge: contract tests green, no val KPI gate in
   `docs/_eval/gates.yaml` regresses, run record appended (I-10).

## V&V loop (mandatory, per phase)

```text
1 Observe current state → 2 Compare vs phase goal → 3 Identify gap →
4 Design smallest safe change → 5 Implement → 6 Focused test → 7 Run app →
8 Record result → 9 Fix → 10 Re-test → 11 Update docs →
12 User review gate → 13 Incorporate feedback → 14 Next phase after approval
```

Recorded per phase in `docs/phase_execution/phase_N_vnv_loop_report.md` as:

| Loop ID | Phase | Issue/Goal | Evidence | Hypothesis | Change Made | Validation Command | Result | Exit Decision |
|---|---|---|---|---|---|---|---|---|

## Data hygiene rules

- **Val split drives all iteration.** Test rows/files are readable only by the
  future `scripts/eval_test.py` (I-4). Phase 12 adds a mechanical quarantine
  guard (audit R-8).
- Weak labels (`label_status: weak_signal_derived`) may seed pretext training
  but never appear as headline accuracy numbers without the caveat; gold
  mini-set numbers are reported separately (audit R-1).
- Video-derived temporal metrics always carry the `sync_provenance:
  constructed` caveat (I-8, audit R-2).

## Phase-specific validation highlights

| Phase | Sharpest check |
|---|---|
| 3 | Meta-test: `src/features/vibration.py` RMS == ETL sliding-RMS on shared input (I-3 unification proof) |
| 4 | Encoder determinism: two runs, same seed → identical Hvib; val AUROC ≥ heuristic baseline |
| 6 | 100% evidence-ID resolvability over val (gate G2) |
| 7 | Stub mode is transparent: output marked `stub`, never presented as model output |
| 8 | Property test: all AlignedTuples chronologically consistent; spans inside [-60,+30] |
| 11 | schema_valid_rate = 1.0 via GBNF path (G1); B1 free-text baseline measurably worse on validity |
| 12 | Prior runs re-scored after any metric change; scores reproduce bit-identically with same seed |
