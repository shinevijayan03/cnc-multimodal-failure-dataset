# Codebase Context

## What The Project Does

Claim:
- The project builds and explores a multimodal CNC failure-explanation dataset made from vibration/sensor windows, video clips, and SOP/maintenance text chunks.

Evidence:
- `README.md` describes a "multimodal CNC failure-explanation dataset" linking vibration, video, maintenance documentation, and labels.
- `src/cli.py` exposes ETL stages `sensor`, `text`, `video`, `assemble`, and `evaluate`.
- `streamlit_app.py` renders incident evidence tabs for video, vibration, SOP text, alignment, and raw row.
- Processed artifacts exist: `incidents.parquet`, `sensor_windows.parquet`, `text_chunks.parquet`, and `video_index.parquet`.

## Main User Journey

1. Install dependencies with `python -m pip install -r requirements.txt`.
2. Stage raw data under `data_pipeline/data_raw`.
3. Build modality indexes with `python -m src.cli all --config config/dataset.yaml`.
4. Evaluate the build with `python -m src.cli evaluate --tier mvp`.
5. Browse evidence with `streamlit run streamlit_app.py`.

Evidence:
- README quickstart lists these commands.
- `python -m src.cli --help` lists the matching commands.
- `Invoke-WebRequest http://localhost:8501` returned `HTTP_STATUS=200`.

## Main Modules and Responsibilities

| Module | Responsibility | Evidence |
|---|---|---|
| `src/cli.py` | Command-line orchestration | Typer commands call `SensorETL`, `TextETL`, `VideoETL`, `IncidentAssembler`, and `evaluate_build` |
| `src/common/config.py` | Typed YAML config | `load_config()` returns `PipelineConfig` and validates paths/schema |
| `src/common/schemas.py` | Row contracts | Pydantic models define output rows used by ETL and tests |
| `src/etl/sensor_etl.py` | Sensor ingestion and windowing | Classes `SensorETL`, `Normalizer`, `EventDetector`, `WindowCarver` |
| `src/etl/text_etl.py` | Manual parsing and chunking | Classes `TextETL`, `DocReader`, `Chunker`, `TopicTagger` |
| `src/etl/video_etl.py` | Video indexing and normalization | Classes `VideoETL`, `FfprobeReader`, `FfmpegNormalizer`, `TagMerger` |
| `src/etl/assemble_incidents.py` | Cross-modal join | `IncidentAssembler` combines sensor, text, and video indexes |
| `src/evaluate.py` | Metrics and grade | `evaluate_build()` writes evaluation reports |
| `src/ui/incident_explorer.py` | UI data access and display helpers | Loads Parquet files and maps incident evidence |
| `streamlit_app.py` | Streamlit page | Defines UI layout and `main()` |

## Data Flow

Evidence-backed flow:
- Sensor raw files under `paths.raw_sensor_root` -> `SensorETL` -> `sensor_windows.parquet` and per-incident files under `sensor_windows/`.
- Text manuals under `paths.raw_text_root` -> `TextETL` -> `text_chunks.parquet`.
- Video files and tags under `paths.raw_video_root` and `video.tagging_csv` -> `VideoETL` -> `video_index.parquet` and normalized video folder.
- `IncidentAssembler` reads the three indexes and writes `incidents.parquet`.
- `evaluate_build()` reads generated indexes and writes `eval_report.json` and `eval_report.md`.
- `streamlit_app.py` reads `data_pipeline/data_processed` by default through `src.ui.incident_explorer.load_pipeline_tables()`.

## How The Application Starts

CLI:
- `python -m src.cli --help` worked and listed commands.
- `python -m src.cli evaluate --config config/dataset.yaml --tier mvp` worked with grade `WARN`.

Web UI:
- Command line observed for running process: `python -m streamlit run streamlit_app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false`.
- URL verified: `http://localhost:8501`, HTTP 200.

## How The Application Is Tested

Evidence:
- `pyproject.toml` sets pytest `testpaths = ["tests"]`.
- `.github/workflows/ci.yml` runs `pytest -q --cov=src --cov-report=term-missing`.
- Local run passed: `87 passed in 45.58s`, total coverage `82%`.

## Supported Assumptions

| Assumption | Status | Evidence |
|---|---|---|
| This is a local file-backed pipeline rather than a database-backed app | Supported | Config paths point to local files; no database dependencies found |
| Streamlit is the primary interactive UI | Supported | `streamlit_app.py`, README, dependency list, HTTP 200 |
| CLI ETL is the primary build path | Supported | README quickstart and `src/cli.py` commands |
| The current processed dataset is usable for UI testing | Supported | Required Parquet artifacts present and UI HTTP check passed |
| The current dataset quality is not final | Supported | Evaluation grade `WARN` due unknown labels and class imbalance |

## Inferences

- Inference: The UI is intended for evidence inspection rather than editing data. Evidence: `streamlit_app.py` only loads, selects, charts, and displays incident rows; no write controls were found.
- Inference: Refactoring should preserve Parquet contracts. Evidence: schemas, tests, UI helpers, and assembler all depend on the same artifact columns.

## Unknowns

- Unknown: Whether the current raw data licensing is acceptable for final dissertation distribution. Evidence needed: source/license records outside current command outputs.
- Unknown: Whether the dirty working tree represents user-approved changes. Evidence needed: user confirmation or git history outside this audit.
- Unknown: Whether the Streamlit UI renders every incident without front-end exceptions. Evidence: only root HTTP response and backend availability were checked, not browser interaction across incident selections.

