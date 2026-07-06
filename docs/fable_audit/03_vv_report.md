# 03 — V&V Report (all verifications executed 2026-07-03 in this session)

| Item | Expected Behavior | Evidence From Code | Verification Method | Result | Issue Found |
|---|---|---|---|---|---|
| Full test suite | all green | 210 tests across 5 layers | `pytest -q` | **PASS** — 209 passed, 1 skipped (opt-in browser smoke) | — |
| Lint | clean | ruff config in pyproject | `ruff check src tests contracts scripts streamlit_app.py` | **PASS** | — |
| Dataset gate | PASS at mvp tier | `src/evaluate.py` TIERS + hard gates | `python -m src.cli evaluate --tier mvp` | **PASS** (GRADE: PASS, 1702 incidents) | — |
| E2E backend chain | ETL→…→grounding works on synthetic data | `tests/integration/test_e2e_tgfx.py` | 4 integration tests (incl. broken-graph refusal) | **PASS** | — |
| I-2 evidence resolution | every emitted id resolves; failures loud | `grounding.py:74-76` raise; `evidence_graph.resolve` KeyError | real-corpus grounding run: 13,596 ids, rate 1.0; refusal test deletes a node → KeyError | **PASS** | — |
| I-3 one feature path | no duplicated feature math | ETL delegates to `sliding_rms`; UI/producers import `rms/spectral_bands` | agreement meta-test (rel 1e-9) + source-inspection test | **PASS** | — |
| I-4 quarantine | test split unreadable by model code | `encoder/data.py::load_tokens` raises PermissionError on "test"; hvib built train/val-only; UI shows "quarantined" | unit test + UI code path | **PASS** (mechanical for encoder path; convention elsewhere — see issue R-8) | partial coverage |
| I-5 determinism | seeded, reproducible | `--seed` defaults 20260702; CUBLAS_WORKSPACE_CONFIG; torch deterministic algorithms | same-seed encoder re-runs bit-identical (Phase 4); byte-identical sample-data generator test | **PASS** | — |
| I-1 frozen VLM | no gradients touch the VLM | `summarizer.py`: eval() + requires_grad_(False) + no_grad + greedy; no training code exists | code inspection; no optimizer anywhere in `src/vision/` | **PASS** | — |
| I-8 sync provenance | constructed-sync caveat travels | hardcoded in ledger, graph edges, clip_summaries, UI tooltips, run-record notes | grep + artifact inspection | **PASS** | — |
| Encoder ≥ heuristic (roadmap gate) | learned anomaly beats floor | run record `encoder_autoencoder_20260702_…` | AUROC 0.5798 (AE) > 0.5198 (baseline) > 0.4170 (heuristic) on val vs real recovered labels | **PASS** (diagnostic; run-level labels, caveat recorded) | weak signal, honest |
| VLM summaries | 20/20 real, deterministic decode | `build_summaries` log | run: mode `vlm` ×20, mean conf 0.95, 492 s | **PASS** | first attempt was slow (fixed: max_pixels cap) |
| Grounding metrics | tuples for all incidents; run record | grounding run output + `docs/_eval/runs.jsonl` tail | 3399 tuples, 1702/1702, G2=true | **PASS** | — |
| App runtime | starts, renders, syncs, exports | AppTest tests + healthz | 3 in-process render/interaction tests; `GET /healthz` → 200 | **PASS** | video sync one-way (platform limit, documented) |
| Fresh-clone path | runnable without staged data | `scripts/generate_sample_data.py` + sample config | sample chain rebuilt through grounding this phase (9 tuples, resolution 1.0) | **PASS** | — |
| Explanation generation | — | Not found in current codebase evidence | — | **UNKNOWN/N.A.** (unbuilt Phase 11) | roadmap gap |
| KPI gates G3/G7–G11 | real-system evaluation | `docs/_eval/gates.yaml` marks fixture_only/deferred | inspection | **PARTIAL** (by design until Phase 12) | roadmap gap |

**Overall V&V: PASS** for everything implemented; unbuilt roadmap phases are
marked UNKNOWN/PARTIAL by design, not silent failures.
