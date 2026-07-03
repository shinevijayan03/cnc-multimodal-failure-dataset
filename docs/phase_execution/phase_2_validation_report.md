# Phase 2 — Validation Report (2026-07-03)

## 1. Focused tests

`python -m pytest tests/unit/test_tgfx_windows.py -q` → **11 passed in 0.60s**

Covered: staged ±8 s span (2 windows, exact IDs/spans), full [-60,+30] span
(27 windows), short span (zero windows), bounds clipping, bad-params rejection,
query-window full/clipped/no-overlap cases, fixture-scheme ID regex +
determinism, driver frame over synthetic waveforms (incl. short-span row with
null window_id), missing-`t_rel_s` rejection.

## 2. Full suite + lint

- `python -m pytest -q` → **121 passed, 1 skipped in 8.85s** (was 110; +11)
- `ruff check src tests contracts scripts` → All checks passed!

## 3. Runtime — real corpus build

`python -m src.tgfx.windows --config config/dataset.yaml` →

```json
{"incidents": 1702, "subwindows": 3399, "short_span_incidents": 0,
 "mean_query_coverage": 0.6664, "out": ".../data_processed/subwindows.parquet"}
```

Sample corpus (`--config config/dataset.sample.yaml --show 4`): 5 incidents →
9 sub-windows; printed rows show `SW_inc_sample_cnc_*_NN` IDs, spans
[-8,+4]/[-5,+7], query [-8,0], coverage 0.6667, `query_clipped=True`.

## 4. Ratchet / no-regression (I-10)

- `python -m src.cli evaluate --config config/dataset.yaml --tier mvp` →
  **GRADE: PASS** (unchanged from Phase 1 / audit).
- `src/eval/` untouched → no meta-test re-run required (I-6 not triggered).
- No KPI gate in `docs/_eval/gates.yaml` is affected; this phase produced
  dataset-structural counts (traced to the commands above), not model metrics,
  so no `runs.jsonl` record is required (I-5/I-7).

## 5. D10 conformance spot-checks

| D10 clause | Verified by |
|---|---|
| 12 s sub-windows, stride 3 | `test_carve_staged_span_yields_two_windows`, `test_carve_full_convention_span` |
| Clipped to [-60,+30] | `test_carve_clips_to_incident_bounds` |
| Query window [-12,0] default | `resolve_query_window` constants + tests |
| Available span used, recorded, never padded | `test_carve_short_span_yields_none`, `test_query_window_no_overlap_is_empty_not_padded`, driver short-span row |
| Evidence IDs resolve in the fixture scheme | `test_sensor_evidence_id_matches_fixture_scheme` |

## Verdict

Phase 2 Definition of Done: **all items met.**
