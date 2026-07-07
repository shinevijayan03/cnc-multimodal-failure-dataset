# Phase 3 — Goal

**Title:** Patch creation + sensor feature extraction (deep-build DB-1).

1. Add **4-band spectral energy** to the one feature path
   (`contracts.core.SensorWindow.spectral_energy` fixes n=4) — I-3.
2. **Retire the I-3 violation** flagged in the audit (risk R-5): the sensor
   ETL's sliding-RMS implementation moves verbatim into
   `src/features/vibration.py`; the ETL imports it. Event detection must stay
   numerically identical (incident IDs must not change).
3. **Patch creation**: 12 s sub-window → PatchTST-style tokens
   (n_patches, n_channels, patch_samples); geometry recorded as decision D12.
4. **Sensor feature producer**: for every Phase 2 sub-window emit RMS,
   spectral bands, kurtosis, variance (one feature path), a heuristic
   anomaly score, the important sensor interval, patch geometry, and a
   sha256 of the raw window; assert `SensorWindow` contract conformance on a
   sample; persist `sensor_features.parquet`.

## Entry criteria (met)

- Phase 2 approved; UI refactor approved ("Approved and now move to Build
  Phase 3"); tree clean at `529373b`.
- `subwindows.parquet` exists for real (3399 windows) and sample corpora.

## Definition of done

- Feature functions unit-tested (tone localization, DC immunity, degenerate
  inputs); sliding-RMS agreement meta-test green (I-3 proof).
- Full suite green (ETL integration tests prove event detection unchanged).
- Producer runs on sample + real corpora; contract sample validation passes.
- `evaluate --tier mvp` still grades PASS (I-10).
- D12 recorded; phase docs written; user review gate posted.
