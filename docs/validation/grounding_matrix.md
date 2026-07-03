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

### Phase 1 (2026-07-03)

| Claim | Evidence Source | File/Command/Test/Log | Confidence | Inference? | Status |
|---|---|---|---|---|---|
| Fresh-clone bootstrap works end-to-end | command | `python scripts/generate_sample_data.py` then `python -m src.cli all --config config/dataset.sample.yaml` → sensor 5 / text 13 / video 2 / assemble 5 written, exit 0 | High | No | Verified |
| Sample path cannot touch real data | files | `config/dataset.sample.yaml` paths all under `*_sample`; gitignored | High | No | Verified |
| Generator is deterministic | test | `tests/unit/test_sample_data.py::test_generation_is_deterministic` (byte-identical) | High | No | Verified |
| Suite green incl. new tests | command | `pytest -q --cov...` → 110 passed, 1 skipped | High | No | Verified |
| Coverage is 80% (now measured, was README-reported) | command | same run → TOTAL 2340/466 = 80% | High | No | Verified |
| GPU: RTX 3060 12 GB, CUDA usable from torch | command | `nvidia-smi`; `torch 2.6.0+cu124 cuda_available True` | High | No | Verified |
| Qwen2.5-VL-7B fp16 will not fit 12 GB VRAM | sizing arithmetic (7B × 2 bytes + vision tower + KV cache ≈ 15–16 GB) | reported in D11; to be confirmed empirically at Phase 7 entry | Medium | Yes | Inference |
| No application code modified in Phase 1 | command | `git status` diff set: scripts/config/tests/docs only | High | No | Verified |
