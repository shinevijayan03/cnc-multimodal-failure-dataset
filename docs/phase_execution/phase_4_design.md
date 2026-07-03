# Phase 4 — Design (decision D13)

## Input representation — patch-feature tokens

The encoder consumes, per 12 s sub-window, a **(95 patches × 15 features)**
matrix flattened to 1425 float32 values: per patch and channel, RMS + the 4
spectral bands, all computed by the one feature path (I-3;
`src/encoder/data.py::patch_tokens_for_window` imports `rms`/`spectral_bands`
and reuses `make_patches` from D12).

*Why feature tokens instead of raw patches (PatchTST-style raw input)?*
Raw patches are 3399 × 95 × 3 × 500 float64 ≈ 3.9 GB in memory and slow to
iterate per epoch; the feature tokens are 19 MB, train in seconds on the RTX
3060, and keep every input dimension physically interpretable. Raw-patch
PatchTST remains a config-selectable future encoder (`encoder.kind`), which is
exactly what the abstraction is for. Recorded as **D13**.

## Components

| Piece | Design |
|---|---|
| `src/encoder/base.py` | `SensorEncoder` ABC (`fit` / `encode` / `anomaly_scores`) + `build_encoder` factory keyed by `encoder.kind` |
| `src/encoder/baseline.py` | Standardize on train stats → seeded Gaussian random projection to `dim` (Hvib); anomaly = norm distance / train q99, clipped to [0,1]. Deterministic, torch-free |
| `src/encoder/torch_ae.py` | MLP AE 1425→256→64(Hvib)→256→1425, MSE, Adam; anomaly = recon error / train q99. `device='cuda'` required per D11 (raises informatively without GPU; tests pass `cpu` explicitly). Seeded via `torch.manual_seed` + `use_deterministic_algorithms(True)` + `CUBLAS_WORKSPACE_CONFIG` |
| `src/encoder/data.py` | Token cache builder (`encoder_tokens.parquet`) + `load_tokens(splits)` that **refuses the test split with PermissionError** (I-4 guard) |
| `src/encoder/train.py` | Seeded CLI: fit on train, evaluate on val, AUROC diagnostic vs quality labels, compare against the Phase 3 heuristic, persist `hvib.parquet` + `models/encoder_<kind>_<seed>.pt`, append run record (imports `append_run_record` from `src.eval.run` — src/eval itself untouched, I-6) |
| `scripts/derive_quality_labels.py` | Re-runs reader+detector deterministically over the raw tree → same incident ids → attaches the real good/bad folder label; writes `docs/_data/quality_labels.jsonl` (committed provenance, like the alignment ledger) |

## Label semantics (honesty per I-7 / audit R-1)

The recovered labels are **real but run-level**: every sub-window inherits its
source run's good/bad folder. They are suitable as a *training diagnostic*
target (is the anomaly score ranking bad runs above good ones?), not as
window-level gold evidence spans. The run-record `notes` field carries this
caveat verbatim. The official KPI gates (G3 AUROC etc.) remain fixture-only
until Phase 12; nothing in `src/eval/` changed.

## Anomaly-score semantics

Self-supervised: the AE learns to reconstruct the dominant (normal) machining
regime from train windows; windows it reconstructs poorly get high scores.
Scores normalize by the train 99th-percentile error, so train scores center
below ~0.5 and unseen regimes saturate toward 1.0.

## Config

New optional `encoder:` section (kind/dim/hidden/epochs/batch_size/lr/device),
defaulted in `PipelineConfig` so existing configs stay valid; the sample
config pins `kind: baseline` to keep the fresh-clone smoke path torch-free.
`pyproject.toml` gains the `encoder = ["torch>=2.2"]` extra and registers
`src.encoder`.
