# CNC Multimodal Failure-Explanation Dataset Pipeline ("Recipe A")

Data-engineering pipeline that builds a **multimodal CNC failure-explanation
dataset** for the dissertation:

> *Temporally Grounded Evidence-Linked Failure Explanation Using Vibration
> Time-Series, Machine Video Streams, and Maintenance Documentation.*

Each output sample is an **incident window** around a machining event that links:
vibration/sensor time-series · a short CNC video clip · relevant SOP &
maintenance text chunks · labels (failure family, regime, phase, severity).

## Status

**Phase 2 — Implementation (complete).** All four ETL stages, the CLI, the
evaluation module, and the test suite are implemented. A demo build over the
staged data produces a valid `incidents.parquet`.

| Phase | Scope | State |
|-------|-------|-------|
| 1 | Understanding, architecture, software design, test & eval strategy | ✅ approved |
| 2 | Implement `sensor_etl`, `video_etl`, `text_etl`, `assemble_incidents` + tests | ✅ done (76 tests green, ~80% cov) |
| 3 | Scale to thesis targets + iterate on evaluation metrics | ⏳ in progress |

## Quickstart

```bash
python -m pip install -r requirements.txt          # ffmpeg must be installed separately for video
python -m src.cli all --config config/dataset.yaml # sensor -> text -> video -> assemble
python -m src.cli evaluate --tier mvp              # grade PASS/WARN/FAIL + write eval_report.{json,md}
```

Per-stage (each supports `--limit N` and `--dry-run`):

```bash
python -m src.cli sensor --limit 200   # build sensor windows from a subset
python -m src.cli text                 # chunk SOP/maintenance manuals (md/txt/docx/pdf)
python -m src.cli video                # normalize clips via ffmpeg (skipped cleanly if absent)
python -m src.cli assemble             # join the three indices -> incidents.parquet
pytest -q                              # run the test suite
```

> **Demo-build note.** The staged Bosch-style corpus is *continuous machining*,
> so `config/dataset.yaml` uses `event_detection.threshold_kind: quantile`
> (the cut itself is the "event") rather than the z-score-for-transients default.
> Without ffmpeg the video stage is skipped, so demo incidents have no video link
> (an honest WARN in the evaluation, recorded per row via `alignment_method`).

## Design documents (read in this order)

1. [Recipe A Overview](docs/recipe_a_overview.md) — what we are building and why
2. [Implementation Plan](docs/implementation_plan.md) — step-by-step build plan
3. [Architecture](docs/architecture.md) — system + data-flow architecture
4. [Software Design](docs/software_design.md) — modules, classes, data models
5. [Test Strategy & Plan](docs/test_strategy_and_plan.md)
6. [Test Cases](docs/test_cases.md)
7. [Evaluation Criteria](docs/evaluation_criteria.md)

## Repository layout

```
data_pipeline/
├── config/dataset.yaml      # single source of truth for all knobs
├── data_raw/                # user-supplied raw inputs (gitignored)
│   ├── <sensor datasets>/   # bosch_cnc, kaggle_cnc, cnc_mill_tool_wear, ...
│   ├── video_raw/           # raw MP4s + video_tags.csv
│   └── text_manuals/        # SOP + maintenance docs (md/txt/docx/pdf)
├── data_processed/          # pipeline outputs (gitignored)
│   ├── sensor_windows/      # per-incident parquet
│   ├── sensor_windows.parquet, video_index.parquet,
│   ├── text_chunks.parquet, incidents.parquet
├── src/                     # etl stages + common modules + cli.py + evaluate.py
├── tests/                   # unit + integration (pytest)
├── notebooks/               # evaluation notebook
└── docs/                    # design artifacts (this phase)
```

## How raw data is supplied

Code never auto-downloads licensed/auth-gated datasets. Place raw files under
`data_raw/<dataset>/` manually; the ETL reads them once present. See
[Recipe A Overview](docs/recipe_a_overview.md) for sources and licensing notes.
