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

### Phase 2 (2026-07-03)

| Claim | Evidence Source | File/Command/Test/Log | Confidence | Inference? | Status |
|---|---|---|---|---|---|
| D10 carving implemented (12 s / stride 3 / clipped to [-60,+30] / no padding) | code + tests | `src/tgfx/windows.py`; `pytest tests/unit/test_tgfx_windows.py -q` → 11 passed | High | No | Verified |
| SW_* IDs byte-compatible with eval fixture scheme | test | `test_sensor_evidence_id_matches_fixture_scheme` vs `src/eval/fixtures.py` (`SW_inc_oracle_001_00`) | High | No | Verified |
| Real corpus: 1702 incidents → 3399 sub-windows, 0 short spans, mean query coverage 0.6664 | command | `python -m src.tgfx.windows --config config/dataset.yaml` JSON summary | High | No | Verified |
| Staged recordings cover only ±8 s of the convention → query coverage ≈ 0.67 by construction | command output + D10 | same summary; `--show` rows (query [-8,0], clipped=True) | High | No | Verified |
| No val KPI regression from Phase 2 | command | `python -m src.cli evaluate --tier mvp` → GRADE: PASS; `src/eval/` untouched | High | No | Verified |
| Suite green after phase | command | `pytest -q` → 121 passed, 1 skipped | High | No | Verified |

### UI temporal alignment refactor (2026-07-03)

| Claim | Evidence Source | File/Command/Test/Log | Confidence | Inference? | Status |
|---|---|---|---|---|---|
| Workbench UI matches reference shots; unified 0-based axis fixes video/sensor misalignment | code + tests + user confirmation | `src/ui/workbench.py`, `streamlit_app.py`; AppTest render tests; user: "yes" (DEMO matches) | High | No | Verified |
| Light theme applied per user's original-UI screenshot | files + user approval | `.streamlit/config.toml`; "Approved and now move to Build Phase 3" | High | No | Verified |
| Suite after UI phases | command | `pytest -q` → 144 passed, 1 skipped | High | No | Verified |

### Phase 3 (2026-07-03)

| Claim | Evidence Source | File/Command/Test/Log | Confidence | Inference? | Status |
|---|---|---|---|---|---|
| Spectral bands (4) live on the one feature path and localize tones correctly | tests | `test_spectral_bands_localize_known_tones`, `..._ignore_dc_offset` | High | No | Verified |
| ETL sliding-RMS unified into the feature path with identical numerics (I-3, audit R-5 retired) | tests | agreement meta-test rel 1e-9; ETL source contains no own math; integration tests unchanged (164 passed) | High | No | Verified |
| Patch geometry per D12: 12 s @ 2 kHz → 95 × 3 × 500, tails dropped | tests + corpus | `test_patch_spec_geometry_matches_d12`; real corpus `n_patches` uniformly 95 | High | No | Verified |
| Real corpus features: 3399 windows, 0 skipped, unique IDs + sha256s, contract sample validated | command | `python -m src.tgfx.sensor_features --config config/dataset.yaml` + pandas describe | High | No | Verified |
| Anomaly scores are near zero on the continuous-machining corpus (mean 0.0052) | command output | same summary; expected — sub-windows of a sustained cut resemble each other | High | No | Verified |
| No val KPI regression | command | `evaluate --tier mvp` → GRADE: PASS; `src/eval/` untouched | High | No | Verified |

### Phase 4 (2026-07-03)

| Claim | Evidence Source | File/Command/Test/Log | Confidence | Inference? | Status |
|---|---|---|---|---|---|
| Real good/bad labels recovered for 100% of incidents (70 bad / 1632 good) | command | `scripts/derive_quality_labels.py` summary; full coverage proves deterministic id re-derivation | High | No | Verified |
| GPU training deterministic (same seed → bit-identical metrics) | commands | two runs seed 20260702: identical final_epoch_loss / val_recon / AUROC | High | No | Verified |
| Encoder beats heuristic and baseline on val (0.5798 > 0.5198 > 0.4170) | run record + command | `docs/_eval/runs.jsonl` encoder_autoencoder_20260702_…; `--kind baseline --no-write` output | High | No | Verified (diagnostic, run-level labels — caveat in record) |
| Test split mechanically refused by the token loader | test | `test_load_tokens_refuses_test_split` (PermissionError) | High | No | Verified |
| cuBLAS determinism issue found + fixed on the RTX 3060 | log + code | first cuda run RuntimeError; `torch_ae.py` sets CUBLAS_WORKSPACE_CONFIG | High | No | Verified |
| Suite green after phase | command | `pytest -q` → 174 passed, 1 skipped | High | No | Verified |
