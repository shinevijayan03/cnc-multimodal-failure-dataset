# Phase 2 — Implementation Log (2026-07-03)

Base commit: `e53b174`.

## Files created

| File | Purpose | ~Lines |
|---|---|---|
| `src/tgfx/windows.py` | D10 carving/query core + parquet driver + CLI | 200 |
| `tests/unit/test_tgfx_windows.py` | 11 unit tests (carving, query, IDs, driver) | 120 |
| `docs/phase_execution/phase_2_*.md` | ETVX record set | — |

## Files edited

| File | Change |
|---|---|
| `src/common/config.py` | `PathsCfg.subwindows_index` (one line, defaulted — backward compatible) |
| `config/dataset.yaml`, `config/dataset.sample.yaml` | Explicit `subwindows_index` path entries |
| `docs/validation/grounding_matrix.md` | Phase 2 rows appended |

Application code touched: `src/tgfx/windows.py` (new), `src/common/config.py`
(+1 line). No ETL, contract, or eval module modified — the I-6 metric freeze
was not triggered.

## Issues hit and fixed

1. Removed an unused `asdict` import and an unnecessary `__all__` block from
   `windows.py` on self-review (ruff would have flagged the import).
2. First real-corpus run confirmed the audit's expectation: staged spans are
   ±8 s, so every incident gets exactly 2 sub-windows ([-8,+4], [-5,+7]) and a
   clipped query window [-8, 0] with coverage ≈ 0.667. One sample incident
   (`inc_sample_cnc_6f61e486a81d`, span end 6.75 s) carved only 1 sub-window —
   the carver handled the ragged span correctly without special-casing.

## Outputs produced (gitignored artifacts)

- `data_pipeline/data_processed/subwindows.parquet` — 1702 incidents →
  **3399 sub-windows**, 0 short-span incidents, mean query coverage 0.6664.
- `data_pipeline/data_processed_sample/subwindows.parquet` — 5 incidents →
  9 sub-windows.
