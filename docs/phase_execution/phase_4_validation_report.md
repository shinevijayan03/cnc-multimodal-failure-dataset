# Phase 4 — Validation Report (2026-07-03)

## 1. Focused tests

`pytest tests/unit/test_encoder.py -q` → **10 passed** (after one loop fix, see V&V).

Covered: token shape (95×15) + I-3 spot-check (token RMS == `rms()` of the
patch); baseline shapes/determinism/outlier-flagging/fit-required; AE loss
decreases, encode shape, scores in [0,1], **bit-identical outputs across two
same-seed instances**, regime-shift saturation; `load_tokens` refuses the test
split (PermissionError, I-4); AUROC known orderings incl. ties and
degenerate single-class NaN; quality-label JSONL parsing.

## 2. Full suite + lint

- `pytest -q` → **174 passed, 1 skipped in 27.08s** (was 164; +10; zero broken)
- `ruff check src tests contracts scripts streamlit_app.py` → All checks passed!

## 3. Quality-label recovery (real corpus)

`python scripts/derive_quality_labels.py --config config/dataset.yaml` →
**1702/1702 incidents labeled** (bad 70 / good 1632), written to
`docs/_data/quality_labels.jsonl`. Full coverage proves the deterministic
re-derivation reproduced every existing incident id exactly.

## 4. Token cache

3399 windows × token_dim 1425 → `encoder_tokens.parquet`.

## 5. GPU training (RTX 3060, per D11)

`python -m src.encoder.train --config config/dataset.yaml --seed 20260702`:

| Metric | Value |
|---|---|
| device | cuda |
| train windows / val windows | 2381 / 509 (test quarantined) |
| loss first → final epoch (20) | 0.875284 → 0.290891 |
| val recon MSE | 0.442329 |
| **val AUROC vs quality — autoencoder** | **0.5798** |
| val AUROC vs quality — baseline encoder | 0.5198 (`--kind baseline` diagnostic run) |
| **val AUROC vs quality — Phase 3 heuristic** | **0.4170** |
| val positives / negatives | 21 / 488 |
| artifacts | `models/encoder_autoencoder_20260702.pt`, `data_processed/hvib.parquet` |

**Roadmap gate met:** encoder (0.5798) ≥ heuristic (0.4170); it also beats the
non-learned baseline (0.5198). Determinism verified: an immediate re-run with
the same seed reproduced `final_epoch_loss`, `val_recon_mse_mean`, and
`val_auroc_quality_encoder` bit-identically.

## 6. Run record (I-5/I-7)

Appended to `docs/_eval/runs.jsonl`:
`run_id=encoder_autoencoder_20260702_20260703T175903+0530`, git_sha `4f34646…`,
seed 20260702, split val, system `encoder_autoencoder`, config/dataset hashes,
metrics incl. AUROCs, notes carrying the run-level-label caveat.

## 7. Ratchet / no-regression (I-10)

- `evaluate --tier mvp` unaffected (no dataset artifact changed; sensor index,
  incidents, chunks untouched).
- `src/eval/` untouched (I-6): the trainer *imports* `append_run_record`; the
  AUROC here is a training diagnostic, clearly named, not gate G3.

## Honest readout

AUROC 0.58 with 21 val positives is a **weak-but-real** signal — expected for
self-supervised reconstruction on run-level labels over continuous machining.
The number's value is (a) it is the project's first metric traceable to a run
record on real labels, and (b) it orders the three systems sensibly
(learned > projection > heuristic). It is not a headline claim (I-7 caveat in
the run record) and does not touch gate G3.
