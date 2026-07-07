# Codex Refactor Changelog

## Purpose

Track Codex-generated Stage A documentation and planning changes.

## 2026-06-20 - Stage A Discovery and Planning

### Added

- Created `docs/refactor_ecosystem/` documentation ecosystem.
- Added execution summary.
- Added codebase inventory.
- Added module breakdown.
- Added architecture document.
- Added software design document.
- Added Markdown refactoring plan and audit.
- Added Streamlit UI design plan.
- Added GPU enablement plan.
- Added integration testing and validation plan.
- Added test case register.
- Added validation matrix.
- Added open-items and pending-tasks register.
- Added next steps document.
- Added phased implementation roadmap.
- Added review and approval checklist.
- Added inventory reports for source tree, dependencies, config, tests, and GPU readiness.
- Added Mermaid diagrams for current architecture, target architecture, module dependencies, runtime flow, and data flow.

### Verified

- `python -m pytest -q`: 76 passed.
- `python -m compileall -q src tests`: passed.
- `python -m src.cli --help`: passed.
- `nvidia-smi`: RTX 3060 visible.
- PyTorch CUDA: available.

### Observed

- `ffmpeg` is missing from PATH.
- Raw data is not staged in `data_raw`.
- `python -m src.cli all --dry-run --limit 1` fails at assembly as expected without a sensor index.
- `python -m src.cli evaluate --tier mvp` fails as expected without `incidents.parquet`.
- `python -m ruff check src tests` reports 8 advisory unused import/variable findings.

### Not Changed

- No source code was refactored.
- No existing Markdown files were edited.
- No Streamlit UI was implemented.
- No GPU code was implemented.
- No generated data outputs were created.

## 2026-06-20 - Stage B Dataset Pipeline Enablement

### Changed

- Updated `config/dataset.yaml` to use the staged `data_pipeline/data_raw` and `data_pipeline/data_processed` folders.
- Disabled missing Bosch H5 input by default and pointed `kaggle_cnc` at `data_pipeline/data_raw/sensor_dataset`.
- Added `segment_center` sensor event mode for short operation-segment CSV files.
- Tuned sensor windowing to 8 seconds before and 8 seconds after the centered event, capped to one window per run.
- Added `text.max_pages_per_doc` and capped staged PDF ingestion at 80 pages per document.
- Expanded video discovery beyond `.mp4`.
- Added raw video indexing fallback when ffmpeg/ffprobe are unavailable.
- Stored generated sensor/video paths relative to the actual repository root.
- Added data-pipeline ignore rules.
- Added video tag template at `data_pipeline/data_raw/video_raw/video_tags.csv`.
- Added `15_PIPELINE_RUNBOOK_AND_BUILD_RESULTS.md`.

### Verified

- `python -m pytest -q`: 78 passed.
- `python -m ruff check src tests`: all checks passed.
- `python -m compileall -q src tests`: passed.
- `python -m src.cli all --config config/dataset.yaml`: completed.
- `python -m src.cli evaluate --config config/dataset.yaml --tier mvp`: completed with `WARN`.

### Generated Dataset Artifacts

- `data_pipeline/data_processed/sensor_windows.parquet`: 1,702 rows.
- `data_pipeline/data_processed/sensor_windows/*.parquet`: 1,702 files.
- `data_pipeline/data_processed/text_chunks.parquet`: 934 rows.
- `data_pipeline/data_processed/video_index.parquet`: 20 rows.
- `data_pipeline/data_processed/incidents.parquet`: 1,702 rows.
- `data_pipeline/data_processed/eval_report.json`: generated.
- `data_pipeline/data_processed/eval_report.md`: generated.
