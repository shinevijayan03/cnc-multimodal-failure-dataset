# Phase 2 — User Review Request

```text
PHASE 2 COMPLETE — USER REVIEW REQUIRED

What changed:
- src/tgfx/windows.py: D10 window convention implemented — 12 s encoder
  sub-windows (stride 3 s), default [-12s, 0s] query window clipped to what
  each recording covers (coverage recorded, never padded), SW_* sensor
  evidence IDs matching the eval fixture scheme.
- subwindows.parquet index added to both configs (real + sample paths).
- 11 new unit tests. ETL, contracts, and eval code untouched.

How to test:
Build the sub-window index and eyeball a few rows.

Commands:
  python -m src.tgfx.windows --config config/dataset.yaml --show 6
  python -m src.tgfx.windows --config config/dataset.sample.yaml --show 6
  pytest -q

Expected result:
  - real corpus: {"incidents": 1702, "subwindows": 3399,
    "short_span_incidents": 0, "mean_query_coverage": 0.6664}
  - rows show window IDs like SW_inc_kaggle_cnc_<hash>_00 with spans
    [-8, +4] / [-5, +7] and query window [-8, 0] (clipped=True)
  - pytest: 121 passed, 1 skipped

Known limitations:
  - Staged 20 s recordings cover only ±8 s of the [-60, +30] convention, so
    query coverage is ~0.67 by construction (recorded per D10, not padded).
  - Sub-windows carry spans + IDs only; rms/spectral/kurtosis/variance and
    patch tokens land in Phase 3 (the feature-path unification).

Please test and provide feedback.
I will incorporate your feedback before moving to Phase 3.
```
