# Phase 1 — Validation Report (2026-07-03)

All commands executed on the dev machine (Windows 11, Python 3.12.7) at the
Phase 1 working tree (base `9c9733f` + Phase 1 changes).

## 1. Fresh-clone bootstrap path

| Step | Command | Result |
|---|---|---|
| Generate | `python scripts/generate_sample_data.py` | 8 sensor CSVs + 2 manuals + tags CSV + 2 ffmpeg clips written to `data_pipeline/data_raw_sample`; `video_status: generated` |
| Full pipeline | `python -m src.cli all --config config/dataset.sample.yaml` | `[sensor] processed=8 written=5` · `[text] written=13` · `[video] written=2 duration_flagged=0` · `[assemble] written=5 no_video=0 short_text=0` — exit 0 |

The sample path wrote only under `data_pipeline/data_processed_sample/`;
the real `data_processed/` artifacts are untouched (paths isolated by config).

## 2. Test suite + coverage (re-measured, replacing README-reported number)

```text
python -m pytest -q --cov=src --cov=contracts --cov=scripts --cov-report=term
110 passed, 1 skipped in 22.57s
TOTAL 2340 stmts, 466 miss, 80%
```

- 4 new tests (`tests/unit/test_sample_data.py`) all pass, including
  byte-identical determinism across same-seed runs.
- 1 skip = opt-in browser smoke (unchanged).
- Coverage lowlights (pre-existing, unchanged by this phase):
  `src/eval/run.py` 0% (CLI-only entry), `src/eval/verify_llm.py` 0%
  (placeholder), `src/features/vibration.py` 41% (kurtosis/delta paths used by
  meta-fixtures only). Targets for Phases 3/12 test work.

## 3. Static checks

- `ruff check src tests contracts scripts` → All checks passed!

## 4. App runtime

- Streamlit headless on port 8601 → `GET /healthz` HTTP 200; stopped cleanly.

## 5. GPU environment (D11)

- `nvidia-smi` → RTX 3060, 12 GB, driver 595.79 / CUDA 13.2.
- `python -c "import torch; ..."` → `torch 2.6.0+cu124 cuda_available True`.

## KPI gates / ratchet (I-10)

No `src/eval/` code changed; no metrics recomputed; no KPI gate affected. No
run record required — this phase produced no model/eval metric (coverage and
test counts are process numbers, traced to the commands above per audit
convention).

## Verdict

Phase 1 Definition of Done: **all items met** (see `phase_1_goal.md`).
