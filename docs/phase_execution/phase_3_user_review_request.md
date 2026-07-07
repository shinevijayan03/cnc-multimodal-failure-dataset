# Phase 3 — User Review Request

```text
PHASE 3 COMPLETE — USER REVIEW REQUIRED

What changed:
- src/features/vibration.py: + spectral_bands (4 equal bands to Nyquist,
  DC-immune), band_edges_hz, sliding_rms (moved verbatim from the ETL — the
  audit's I-3 duplication is retired; event detection numerics unchanged)
- src/features/patching.py: D12 patch tokens — 12 s @ 2 kHz -> 95 patches
  of 500 samples x 3 channels, stride 250, tails dropped
- src/tgfx/sensor_features.py: per-sub-window RMS / 4-band spectral energy /
  kurtosis / variance (one feature path), heuristic anomaly score, important
  sensor interval, patch geometry, sha256; SensorWindow contract validated on
  a sample; writes sensor_features.parquet
- decisions.md D12; config path key; 20 new tests

How to test:
  python -m src.tgfx.sensor_features --config config/dataset.yaml --limit 20
  python -c "import pandas as pd; print(pd.read_parquet('data_pipeline/data_processed/sensor_features.parquet').head(6).to_string())"
  pytest -q

Expected result:
  - summary JSON: windows 3399 (full run) / contract_validated 5 / skipped 0
  - feature rows with SW_* window ids, 4 spec_band columns, n_patches=95
  - pytest: 164 passed, 1 skipped

Known limitations:
  - anomaly_score is a Phase 3 heuristic (RMS rise vs the incident's earliest
    sub-window); near zero on this continuous-machining corpus by nature —
    the trained encoder (Phase 4) replaces it
  - patch tensors are computed on demand, not persisted (3.9 GB if stored)

Please review and approve to start Build Phase 4 (pluggable sensor encoder,
GPU training per D11).
```
