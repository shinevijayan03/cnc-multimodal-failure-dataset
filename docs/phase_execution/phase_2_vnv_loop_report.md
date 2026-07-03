# Phase 2 — V&V Loop Report

| Loop ID | Phase | Issue/Goal | Evidence | Hypothesis | Change Made | Validation Command | Result | Exit Decision |
|---|---|---|---|---|---|---|---|---|
| L2.1 | 2 | No sub-window producer exists (gap matrix #2/#19 partial) | audit `05_current_vs_target_gap_matrix.md` | A pure carve/query core + parquet driver in src/tgfx closes the D10 gap without touching ETL | Added `src/tgfx/windows.py`, `PathsCfg.subwindows_index`, YAML keys | `pytest tests/unit/test_tgfx_windows.py -q` | 11 passed | Continue |
| L2.2 | 2 | Unused import + needless `__all__` in new module | self-review | ruff would flag; remove | Removed `asdict` import + `__all__` | `ruff check src tests contracts scripts` | All checks passed | Continue |
| L2.3 | 2 | Does the carver survive the real corpus? | staged spans ±8 s (audit) | Every incident → 2 sub-windows, clipped query [-8,0] | None (execution) | `python -m src.tgfx.windows --config config/dataset.yaml` | 1702 incidents → 3399 sub-windows, 0 short spans, mean coverage 0.6664 | Continue |
| L2.4 | 2 | 3399 ≠ 1702×2 — why? | sample run showed a 1-window incident (span end 6.75 s) | Ragged/short recordings carve fewer windows; correct D10 behavior, not a bug | None (verified by inspection of sample `--show` output) | `python -m src.tgfx.windows --config config/dataset.sample.yaml --show 4` | 5 incidents → 9 windows incl. one 1-window incident; spans/IDs correct | Continue |
| L2.5 | 2 | Regression risk from config change | `PathsCfg` edited | Defaulted field keeps old configs valid | One-line default | `python -m pytest -q` | 121 passed, 1 skipped | Continue |
| L2.6 | 2 | Ratchet check (I-10) | build must not regress val gates | No eval code touched → PASS expected | None | `python -m src.cli evaluate --tier mvp` | GRADE: PASS | Phase exit → user gate |

No rollbacks. `src/eval/` untouched (I-6 not triggered).
