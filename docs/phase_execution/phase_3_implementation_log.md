# Phase 3 — Implementation Log (2026-07-03)

Base commit: `529373b`.

## Files created

| File | Purpose | ~Lines |
|---|---|---|
| `src/features/patching.py` | D12 patch tokens (spec + make_patches) | 75 |
| `src/tgfx/sensor_features.py` | Sub-window feature producer + contract sample validation + CLI | 210 |
| `tests/unit/test_features_phase3.py` | 12 tests: spectral bands, band edges, sliding-RMS agreement (I-3 meta-test), ETL-delegation source check, patch geometry/content/tail/determinism | 110 |
| `tests/unit/test_sensor_features.py` | 8 tests: exact slicing, DC removal, burst response, sha256 stability, anomaly-score bounds, important interval, contract accept/reject | 100 |
| `docs/phase_execution/phase_3_*.md` | ETVX record set | — |

## Files edited

| File | Change |
|---|---|
| `src/features/vibration.py` | + `spectral_bands`, `band_edges_hz`, `sliding_rms` (moved verbatim from ETL); docstring now names it the ONE feature path (I-3) |
| `src/etl/sensor_etl.py` | `EventDetector._sliding_rms` delegates to the feature path (2 lines); import added |
| `src/common/config.py` | `PathsCfg.sensor_features_index` (defaulted) |
| `config/dataset.yaml`, `config/dataset.sample.yaml` | explicit `sensor_features_index` entries |
| `docs/_sdd/decisions.md` | **D12** — patch geometry (0.25 s / 0.125 s), canonical magnitude signal, 4 bands, heuristic anomaly score |
| `docs/validation/grounding_matrix.md` | Phase 3 rows |

`src/eval/` untouched — the I-6 metric freeze was not triggered (functions
were *added* to the feature path; `rms/variance/kurtosis/feature_delta/rose`
used by the verifier are byte-identical, and the eval meta-tests re-ran green
in the full suite).

## Issues hit and fixed

1. **L3.1 — float-noise slicing**: mask-based window slicing returned 24,001
   samples instead of 24,000 (accumulated float error in `t_rel_s` let one
   extra sample under the `< t_end` cut). Fixed with index-based slicing
   (searchsorted start + exact duration×fs count). Caught by
   `test_window_signal_removes_dc_offset_and_slices_exact_count`.
2. **L3.2 — wrong test expectation**: the important-interval test assumed the
   interval starts ≥1.5 s before the burst; the correct semantics is
   peak-center ±0.5 s. Test corrected to assert burst overlap + containment
   (implementation was right).

## Outputs produced (gitignored artifacts)

| Corpus | Command | Result |
|---|---|---|
| Sample | `python -m src.tgfx.sensor_features --config config/dataset.sample.yaml` | 5 incidents → 9 windows, 5 contract-validated, 0 skipped |
| Real | `python -m src.tgfx.sensor_features --config config/dataset.yaml` | **1702 incidents → 3399 windows**, 5 contract-validated, 0 skipped, mean anomaly 0.0052 |

Distribution sanity (real corpus): rms mean 268.1 / max 856.3; kurtosis mean
4.96 (typical machining vibration); 3399 unique window IDs and 3399 unique
sha256 hashes; `n_patches` uniformly 95 (matches D12 exactly).
