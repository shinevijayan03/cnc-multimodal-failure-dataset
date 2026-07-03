# 08 — Runtime Execution Report

Executed 2026-07-03, Windows 11 Pro (10.0.22000), PowerShell 7, Python 3.12.7
(Anaconda base env), repo at commit `547f2c1`, clean working tree.

## Classification

```text
RUNS
```

Every documented entry point starts and completes successfully with the
locally staged data. No warnings were observed in the captured output beyond
git CRLF notices (unrelated to runtime).

## Evidence per entry point

### 1. Dependency check
- Command: `python -c "import pandas, pydantic, streamlit, typer; print('deps ok')"`
- Result: `deps ok`. No install step was needed (Anaconda env already
  satisfies `requirements.txt`).

### 2. Test suite
- Command: `python -m pytest -q`
- Result: **`106 passed, 1 skipped in 8.17s`**
- Skip: browser UI smoke, opt-in via `RUN_BROWSER_SMOKE=1`
  (`pyproject.toml` markers; `tests/ui/test_streamlit_browser_smoke.py`).

### 3. Dataset evaluation CLI
- Command: `python -m src.cli evaluate --config config/dataset.yaml --tier mvp`
- Result: **`GRADE: PASS`**. Key metrics from stdout:
  - `n_incidents` implied by split_dist sum = 1702
    (`split_dist: {'train': 1192, 'val': 255, 'test': 170, 'human_eval': 85}`)
  - `pct_with_video / pct_with_sop / pct_with_maint / pct_fully_multimodal = 1.0`
  - `failure_family_dist: {'spindle_fault': 597, 'chatter': 571, 'tool_wear': 534}`
    (weak scaffolding labels — see README demo-build note)
  - `regime_dist: {'unknown': 1702}` (regimes never derived)
  - integrity gates all 0.0 (`pct_missing_sensor_file`, `pct_dangling_chunk_id`, …)
  - `text_pages_equiv: 319.07`, `pct_event_near_zero: 1.0`,
    `pct_label_match_alignment: 1.0`, `pct_window_len_mismatch: 0.0029`
- Writes `data_pipeline/data_processed/eval_report.{json,md}`.

### 4. TGFX fixture evaluation harness
- Command: `python -m src.eval.run --fixtures oracle --no-write`
- Result: runs and prints metrics JSON — all 1.0 / 0.0 as expected for the
  oracle fixture (schema_valid_rate 1.0, unsupported_claim_rate 0.0,
  iou_sensor 1.0, attr_precision 1.0, ece 0.0).
- `--no-write` used deliberately so the audit does not append to
  `docs/_eval/runs.jsonl`.

### 5. Streamlit UI
- Command: `python -m streamlit run streamlit_app.py --server.headless true --server.port 8599`
- Result: banner "You can now view your Streamlit app in your browser";
  `GET http://localhost:8599/healthz` → **HTTP 200** within 30 s;
  process stopped cleanly afterwards.

### 6. ETL dry-runs (no writes)
- `python -m src.cli sensor --dry-run --limit 2` →
  `[sensor] [DRY-RUN] discovered=0 processed=2 written=2 skipped=1 errors=0 | incident_hours=0.0089`
- `python -m src.cli text --dry-run --limit 1` →
  `[text] [DRY-RUN] discovered=5 processed=1 written=1 skipped=0 errors=0 | docs=1`
- ffmpeg 8.1.1 present on PATH (video stage is runnable; not re-run to avoid
  touching processed artifacts).

### 7. Static checks
- `ruff check src tests contracts scripts` → `All checks passed!`
- `python -m compileall -q src contracts scripts streamlit_app.py` → OK

## Not executed (with reasons)

| Command | Reason |
|---|---|
| `python scripts/build_dataset.py` | Rewrites tracked files (`docs/_data/*`, `data/splits/*`); behavior already verified by `tests/unit/test_tgfx_dataset.py` in the green suite |
| `python -m src.cli all` (full rebuild) | Long full rebuild over 1702 incidents; artifacts already exist and grade PASS; dry-runs verified stage wiring |
| `python -m src.eval.run` without `--no-write` | Would append an audit-noise record to `docs/_eval/runs.jsonl` |

## Known runtime caveats

1. The pipeline depends on locally staged raw data under
   `data_pipeline/data_raw/` (gitignored). On a fresh clone the ETL discovers
   zero files and the UI shows empty tables — the committed processed parquet
   demo artifacts mitigate this locally but are gitignored too. **Inference:**
   a fresh-clone bootstrap path is a gap for user testing (flagged in risk
   register R-7).
2. Video normalization requires ffmpeg; code skips cleanly when absent
   (`VideoETL._tools_available`, `src/etl/video_etl.py:184`).
