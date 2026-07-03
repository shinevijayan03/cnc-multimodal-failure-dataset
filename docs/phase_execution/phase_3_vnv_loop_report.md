# Phase 3 — V&V Loop Report

| Loop ID | Phase | Issue/Goal | Evidence | Hypothesis | Change Made | Validation Command | Result | Exit Decision |
|---|---|---|---|---|---|---|---|---|
| L3.0 | 3 | RMS duplicated in ETL (audit R-5, I-3) | `sensor_etl.py:246-256` vs feature path | Moving the vectorized code verbatim preserves detection numerics; per-window rewrite risks threshold flips | `sliding_rms` moved to `vibration.py`; ETL delegates | `pytest -q` (incl. ETL integration tests) | 164 passed; 3-burst detection unchanged | Continue |
| L3.1 | 3 | Producer slice returned 24,001 samples (expected 24,000) | `test_window_signal...` failure: `assert 24001 == 24000` | Accumulated float error in `t_rel_s` lets one sample slip under the `< t_end` mask | Index-based slicing: searchsorted start + exact duration×fs count | `pytest tests/unit/test_sensor_features.py -q` | 8 passed; exact counts | Continue |
| L3.2 | 3 | Important-interval test failed (`-1.25 <= -1.5`) | pytest output | Test expectation wrong: interval is peak-center ±0.5 s, so −1.25 is correct for a burst at −1.0..−0.4 | Test corrected to assert burst overlap + containment (implementation untouched) | same | 8 passed | Continue |
| L3.3 | 3 | Does the producer survive the full corpus + contract? | — | 2-min pure-Python feature pass acceptable; sample validation catches schema drift | None (execution) | `python -m src.tgfx.sensor_features --config config/dataset.yaml` | 3399 windows, 0 skipped, 5 contract-validated | Continue |
| L3.4 | 3 | Ratchet check | — | Nothing eval-side changed | None | `python -m src.cli evaluate --tier mvp` | GRADE: PASS | Phase exit → user gate |

No rollbacks. `src/eval/` untouched.
