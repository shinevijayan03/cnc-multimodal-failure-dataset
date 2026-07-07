# Phase 3 — Validation Report (2026-07-03)

## 1. Focused tests

`pytest tests/unit/test_features_phase3.py tests/unit/test_sensor_features.py -q`
→ **20 passed in 1.65s** (after fixing L3.1/L3.2; first run 18/20).

Key assertions:
- 100 Hz tone → band 0; 800 Hz tone → band 3; energy concentration >100×.
- Bosch-style −1015 DC offset does not shift band attribution.
- **I-3 meta-test:** vectorized `sliding_rms` equals per-window `rms()` to
  rel 1e-9 on random signals; ETL delegate contains no own math
  (source-inspected for absence of `cumsum`).
- D12 geometry: 24,000 samples → 95 patches of 500 (stride 250); tails
  dropped; deterministic; short windows rejected.
- Producer: exact 24,000-sample slices despite float noise; burst window has
  higher rms + positive anomaly score; important interval overlaps the burst;
  sha256 stable and content-sensitive; full `SensorWindow` pydantic instance
  accepted; wrong duration rejected.

## 2. Full suite + lint

- `pytest -q` → **164 passed, 1 skipped in 25.21s** (was 144; +20; zero broken)
- Includes the ETL integration tests (3 synthetic bursts → 3 windows) — proof
  that moving sliding-RMS did **not** change event detection.
- `ruff check src tests contracts scripts streamlit_app.py` → All checks passed!

## 3. Runtime — feature builds

| Corpus | Result |
|---|---|
| Sample | 9 windows from 5 incidents; 5 contract-validated; 0 skipped |
| Real | **3399 windows from 1702 incidents**; 5 contract-validated; 0 skipped; 3399 unique IDs + sha256s; n_patches uniformly 95 |

## 4. Ratchet / no-regression (I-10)

- `python -m src.cli evaluate --config config/dataset.yaml --tier mvp` →
  **GRADE: PASS** (unchanged).
- Eval meta-tests re-ran green inside the full suite; `src/eval/` untouched
  (I-6 not triggered); verifier functions byte-identical.
- No `runs.jsonl` record required: this phase produced dataset-structural
  features, not model/eval metrics; all numbers trace to the commands above.

## 5. Project DoD movement

| DoD item | Before | After |
|---|---|---|
| 3. Sensor patches created | ❌ | ✅ (`make_patches`, D12, geometry persisted) |
| 5. Degradation signatures detected | heuristic spans only | ◐ heuristic anomaly_score + important interval per window (encoder in Phase 4) |

## Verdict

Phase 3 Definition of Done: **all items met.**
