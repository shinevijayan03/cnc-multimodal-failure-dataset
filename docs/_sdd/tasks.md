# TGFX Task DAG Status

Source: `C:/Users/Admin/Downloads/master_prompt.md`, section 12.

| Task | Scope | Status | Evidence |
|---|---|---|---|
| T-01 | repo + constitution + contracts | Complete for current substrate | `CLAUDE.md`, `contracts/`, `tests/contracts/`, `docs/_sdd/` |
| T-02/T-03 | dataset loaders, generator, ledger, splits, manifest | Complete for Recipe A artifact substrate | `scripts/build_dataset.py`, `src/tgfx/dataset.py`, `docs/_data/manifest.json`, `docs/_data/alignment_ledger.jsonl`, `data/splits/*.jsonl`, `tests/unit/test_tgfx_dataset.py` |
| T-04/T-06 | evaluation harness, meta-tests, golden mini-set | Complete for fixture/meta-test harness | `src/eval/`, `tests/eval_meta/`, `docs/_eval/runs.jsonl`; `pytest tests/eval_meta -x -q` passes |
| T-10/T-11 | features + encoder train | Not started | `src/features/vibration.py` exists as eval harness feature path; no `src/encoder/` |
| T-12 | VLM summarizer + probe | Not started | no `src/vision/` |
| T-13/T-15 | SOP index, retrieval, evidence graph | Not started | no `src/retrieval/`, no `src/graph/` |
| T-17/T-18 | temporal grounding + selection head | Not started | no `src/temporal/`, no `src/fusion/` |
| T-19/T-21 | decoder + baselines | Not started | no `src/explain/`, no baseline scripts |
| T-22+ | end-to-end TGFX integration and later milestones | Not started | no TGFX runtime pipeline |

Next recommended task:
- Harden TGFX real validation fixtures and evidence graph resolution before
  model/encoder work. The current T-02/T-03 substrate is generated from Recipe A
  artifacts and carries weak label scaffolding, not curated gold labels.
