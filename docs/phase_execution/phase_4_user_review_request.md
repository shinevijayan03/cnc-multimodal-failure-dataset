# Phase 4 — User Review Request

```text
PHASE 4 COMPLETE — USER REVIEW REQUIRED

What changed:
- src/encoder/: SensorEncoder ABC + factory; deterministic projection
  baseline; GPU autoencoder producing Hvib (64-d) + anomaly scores from D13
  patch-feature tokens; seeded training CLI with run records
- scripts/derive_quality_labels.py: recovered the REAL good/bad folder labels
  for all 1702 incidents by deterministic re-derivation (70 bad / 1632 good)
- Mechanical I-4 guard: the token loader refuses the test split
- Config encoder section; torch extra; D13 decision; models/ gitignored

How to test:
  python -m src.encoder.train --config config/dataset.yaml --seed 20260702 --no-write
  Get-Content docs/_eval/runs.jsonl -Tail 1
  pytest -q

Expected result:
  - training on device cuda, loss 0.8753 -> 0.2909 (20 epochs), and
    val_auroc_quality_encoder = 0.5798 vs val_auroc_quality_heuristic = 0.417
    (bit-identical on every same-seed run)
  - last runs.jsonl line: system encoder_autoencoder, seed 20260702
  - pytest: 174 passed, 1 skipped

Known limitations:
  - AUROC 0.58 on 21 val positives is a weak-but-real diagnostic (run-level
    labels, self-supervised encoder) — not a headline number, caveat recorded
    in the run record; official gate G3 remains fixture-only until Phase 12
  - Raw-patch PatchTST deferred (config-selectable encoder.kind later)

GPU report (D11):
  - Issue found & fixed: CUDA determinism requires CUBLAS_WORKSPACE_CONFIG
    (:4096:8); now set automatically by the encoder module
  - No VRAM pressure (tiny MLP + 19 MB tokens on the 12 GB RTX 3060);
    training is seconds per run; determinism verified on-GPU

Please review and approve to start Build Phase 5 (SOP embeddings + vector
store — BGE embeddings will also run on the GPU).
```
