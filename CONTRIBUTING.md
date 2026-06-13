# Contributing / Developer Setup

This is the data-engineering pipeline for the M.Tech thesis *"Temporally
Grounded Evidence-Linked Failure Explanation."* It builds
`data_processed/incidents.parquet` from manually staged raw CNC data.

## 1. Environment

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    |    macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

- **Python ≥ 3.10.**
- **ffmpeg / ffprobe** are external binaries needed only by the video stage.
  Install separately (Windows: `winget install Gyan.FFmpeg`). Without them the
  video stage is skipped cleanly and the rest of the pipeline still runs.
- `tiktoken`, `pypdf`, `python-docx`, `rank-bm25` are optional; the pipeline
  degrades gracefully (e.g. whitespace token counting) if any are missing.

## 2. Staging raw data

The pipeline never auto-downloads licensed data. Place raw files under
`data_raw/<dataset>/` (sensor CSV/H5), `data_raw/video_raw/` (MP4 +
`video_tags.csv`), and `data_raw/text_manuals/` (md/txt/docx/pdf). Everything
under `data_raw/` and `data_processed/` is gitignored.

## 3. Running

```bash
python -m src.cli all --config config/dataset.yaml   # sensor -> text -> video -> assemble
python -m src.cli evaluate --tier mvp                # grade PASS/WARN/FAIL
python -m src.cli sensor --limit 200 --dry-run       # any stage; --limit / --dry-run supported
```

All knobs live in [`config/dataset.yaml`](config/dataset.yaml) — no magic numbers
in code.

## 4. Tests

```bash
pytest -q                 # full suite
pytest -q --cov=src       # with coverage
pytest tests/unit/test_sensor.py -q   # one module
```

Tests are tiny and synthetic (no licensed data). The numeric core
(`EventDetector`, `WindowCarver`, `FsEstimator`, `Chunker`, `SplitAssigner`) is
pure and unit-tested; each stage's `run()` has an integration test over a temp
workspace. Case IDs (`UT-*`, `IT-*`, `E2E-*`) trace back to
[`docs/test_cases.md`](docs/test_cases.md).

## 5. Code layout & extension points

| Area | File |
|------|------|
| Config models + loader | `src/common/config.py` |
| Row schemas (Pydantic) | `src/common/schemas.py` |
| ETL stages | `src/etl/{sensor,text,video,assemble_incidents}.py` |
| CLI / evaluation | `src/cli.py`, `src/evaluate.py` |

Extension hooks (see [`docs/software_design.md`](docs/software_design.md) §11):

- **New sensor format** → add a reader to `READERS` in `sensor_etl.py` + a
  `column_map` in config. No core change.
- **New event detector** → register under `event_detection.method`.
- **New text retrieval / tagging** → swap the strategy object in `assemble`/`text`.

## 6. Style

`ruff` (lint) and `ruff format` are advisory (run in CI, not gating). Keep new
code consistent with the surrounding modules: typed signatures, config-driven
constants, and validated rows written through the schemas.
