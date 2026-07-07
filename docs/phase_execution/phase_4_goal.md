# Phase 4 — Goal

**Title:** Pluggable / trainable sensor encoder (deep-build DB-2).

1. **Encoder abstraction** (`SensorEncoder` ABC + factory) so encoders swap by
   config (`encoder.kind`).
2. **Deterministic non-learned baseline** (seeded random projection +
   distance anomaly) — the floor any learned encoder must beat, torch-free.
3. **Trainable autoencoder** producing **Hvib** embeddings + anomaly scores
   from D13 patch tokens; torch on the local GPU (D11); seeded and
   deterministic (I-5); train/inference separation; checkpoint saved.
4. **Real evaluation target**: recover the raw corpus's good/bad folder
   labels for existing incidents by deterministic re-derivation
   (`scripts/derive_quality_labels.py`) — a genuine binary signal that
   de-circularizes the AUROC diagnostic (audit risk R-1 partially retired).
5. **Run record** appended to `docs/_eval/runs.jsonl` with git_sha,
   config_hash, seed, dataset_manifest_hash (I-5/I-7).
6. **Test-split quarantine enforced in code**: the token loader refuses the
   test split outright (first mechanical I-4 guard, ahead of Phase 12).

## Entry criteria (met)

- Phase 3 approved ("Approve to start Build Phase 4"); tree clean at `4f34646`.
- `subwindows.parquet` + `sensor_features.parquet` exist; torch 2.6.0+cu124
  with CUDA available (Phase 1 GPU baseline).

## Definition of done

- Baseline + autoencoder pass shape/determinism/outlier tests; loss decreases.
- GPU training runs end-to-end; same seed → identical metrics (verified twice).
- Encoder val AUROC vs real quality labels ≥ heuristic baseline (roadmap gate).
- Hvib embeddings persisted for train+val windows; checkpoint saved.
- Run record appended; full suite green; evaluate PASS; docs + user gate.
