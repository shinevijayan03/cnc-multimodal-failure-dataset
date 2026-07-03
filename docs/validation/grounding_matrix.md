# Grounding Matrix (living document)

Every major claim made in audit/build documentation and phase reports must be
listed here. Phase gates append rows; nothing is deleted, only marked stale.

Format:

| Claim | Evidence Source | File/Command/Test/Log | Confidence | Inference? | Status |
|---|---|---|---|---|---|

## Audit stage (2026-07-03, commit 547f2c1)

The complete audit-stage matrix (28 rows) lives at
`docs/architecture_audit/12_grounding_traceability_matrix.md`. Summary of the
load-bearing claims:

| Claim | Evidence Source | File/Command/Test/Log | Confidence | Inference? | Status |
|---|---|---|---|---|---|
| Runtime state is RUNS | commands | pytest 106 pass; evaluate GRADE PASS; streamlit healthz 200; ETL dry-runs | High | No | Verified |
| Dataset substrate complete: 1702 incidents, fully multimodal, integrity gates clean | command | `python -m src.cli evaluate --tier mvp` stdout | High | No | Verified |
| Zero model-side components exist (encoder/VLM/vector-DB/graph/fusion/decoder) | file inventory | no `src/encoder|vision|retrieval|graph|temporal|fusion|explain`; `docs/_sdd/tasks.md` | High | No | Verified |
| Contracts exist but have no producers (AlignedTuple, ExplanationOutput, clip_summary) | files | `contracts/core.py`, `contracts/explanation.py`, `src/eval/fixtures.py` (only hand-authored instances) | High | No | Verified |
| TGFX eval harness runs on fixtures only; AUROC/ECE placeholders | files + command | `src/eval/metrics.py:148,199`; `python -m src.eval.run --no-write` | High | No | Verified |
| Labels are weak scaffolding, not gold | files | README demo note; `docs/_data/manifest.json label_status` | High | No | Verified |
| Video sync provenance constructed | file | `src/tgfx/dataset.py:82` | High | No | Verified |
| Test split contents | — | quarantined per I-4; never read | — | — | Deliberately Unknown |
| CI status of current branch | — | not executed during audit | — | — | Unknown |
| 80% coverage | README snapshot 2026-07-02 | not re-measured | Medium | No | README-reported |

## Build phases

(rows appended at each phase gate — PENDING)
