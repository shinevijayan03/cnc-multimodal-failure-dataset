# Phase 4 — Implementation Log (2026-07-03)

Base commit: `4f34646`.

## Files created

| File | Purpose | ~Lines |
|---|---|---|
| `src/encoder/__init__.py`, `base.py` | ABC + factory (`encoder.kind`) | 60 |
| `src/encoder/data.py` | D13 patch-token builder + cache + split-guarded loader (I-4) | 120 |
| `src/encoder/baseline.py` | Deterministic projection baseline | 50 |
| `src/encoder/torch_ae.py` | GPU autoencoder (Hvib + anomaly), seeded, save() | 140 |
| `src/encoder/train.py` | Training CLI + AUROC diagnostic + run record + hvib.parquet | 190 |
| `scripts/derive_quality_labels.py` | Deterministic good/bad label recovery | 90 |
| `tests/unit/test_encoder.py` | 10 tests | 140 |
| `docs/_data/quality_labels.jsonl` | Recovered run-level labels (1702 rows, committed provenance) | — |
| `docs/phase_execution/phase_4_*.md` | ETVX record set | — |

## Files edited

| File | Change |
|---|---|
| `src/common/config.py` | `EncoderCfg` + optional `encoder` section (defaulted) |
| `config/dataset.yaml` / `dataset.sample.yaml` | `encoder:` sections (sample pins torch-free `baseline`) |
| `pyproject.toml` | `encoder = ["torch>=2.2"]` extra; `src.encoder` package |
| `.gitignore` | `models/` (checkpoints recreatable from seeded training) |
| `.env.example` | `CUBLAS_WORKSPACE_CONFIG` note |
| `docs/_sdd/decisions.md` | **D13** — patch-feature tokens as encoder input; run-level label semantics |
| `docs/_eval/runs.jsonl` | +1 run record (encoder_autoencoder, seed 20260702) |

`src/eval/` untouched (I-6). `src/etl/`, contracts untouched.

## GPU issue found and fixed (reported per D11)

**CUDA determinism requires `CUBLAS_WORKSPACE_CONFIG`.** First GPU training
run crashed: `torch.use_deterministic_algorithms(True)` + cuBLAS on CUDA ≥10.2
demands `CUBLAS_WORKSPACE_CONFIG=:4096:8`. Fixed by setting the env var in
`torch_ae.py` before the first cuBLAS call (documented in `.env.example` for
anyone importing torch earlier). After the fix, GPU training is fully
deterministic — verified by bit-identical metrics across two same-seed runs.
No VRAM pressure: the model is tiny (1425→256→64) and the whole token set is
19 MB; the 12 GB card is barely touched (this phase's real GPU constraint was
determinism, not memory).

## Run sequence (real corpus)

1. `derive_quality_labels` → 1702 labeled (70 bad / 1632 good)
2. `build_token_cache` → 3399 × 1425 tokens
3. `train --seed 20260702` (GPU) → metrics + checkpoint + hvib.parquet + run record
4. same-seed re-run (`--no-write`) → identical metrics (determinism proof)
5. `--kind baseline --no-write` → comparison AUROC 0.5198
