# Phase 4 — V&V Loop Report

| Loop ID | Phase | Issue/Goal | Evidence | Hypothesis | Change Made | Validation Command | Result | Exit Decision |
|---|---|---|---|---|---|---|---|---|
| L4.1 | 4 | AUROC needs a non-circular target (audit R-1) | weak labels are hash-derived; quality label never persisted | The ETL is deterministic → re-running reader+detector re-derives identical incident ids, letting the real folder label attach | `scripts/derive_quality_labels.py` | run on real corpus | **1702/1702 matched** (70 bad / 1632 good) — full coverage proves id fidelity | Continue |
| L4.2 | 4 | Regime-shift test failed (`1.0 > 0.54*2`) | pytest output | Scores clip at 1.0 by normalization design; ×2 threshold wrong for saturating scores | Test asserts saturation (>0.95) + margin over train mean (impl untouched) | `pytest tests/unit/test_encoder.py -q` | 10 passed | Continue |
| L4.3 | 4 | **GPU crash:** deterministic algorithms + cuBLAS | `RuntimeError: ... CUBLAS_WORKSPACE_CONFIG` on first `--device cuda` run | cuBLAS needs the workspace env var before first call | `os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")` in `torch_ae.py`; `.env.example` note | re-run training | Trains on cuda; deterministic | Continue (reported at gate per D11) |
| L4.4 | 4 | Is GPU training deterministic in practice? | I-5 requires it | Seeded torch + deterministic algorithms + cuBLAS config suffice for MLP | None (verification) | same-seed re-run `--no-write` | `final_epoch_loss`, `val_recon_mse_mean`, `val_auroc` bit-identical | Continue |
| L4.5 | 4 | Roadmap gate: encoder ≥ heuristic on val | Phase 3 heuristic AUROC 0.4170 | Recon-error anomaly should at least beat a below-chance heuristic | None (measurement) | `train --seed 20260702` + `--kind baseline --no-write` | AE 0.5798 > baseline 0.5198 > heuristic 0.4170 | Gate met → user review |

No rollbacks. One genuine GPU issue (L4.3) fixed and reported per D11.
