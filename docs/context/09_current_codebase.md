# Current Codebase

## Directory Structure

Verified top-level structure:
- `.github/workflows/ci.yml`
- `config/dataset.yaml`
- `data_pipeline/`
- `docs/`
- `docs/codebase_audit/`
- `docs/context/`
- `docs/_sdd/`
- `docs/_eval/`
- `docs/_data/`
- `docs/build_iterations/`
- `notebooks/`
- `contracts/`
- `src/`
- `tests/`
- `README.md`
- `pyproject.toml`
- `requirements.txt`
- `streamlit_app.py`

Evidence:
- `rg --files ...`, `git status --short`, `docs/codebase_audit/01_repository_inventory.md`.

## Major Modules

| Module | Purpose |
|---|---|
| `src/cli.py` | Typer CLI entry point |
| `src/evaluate.py` | Dataset quality metrics and grade |
| `src/eval/fixtures.py` | TGFX eval meta-fixtures |
| `src/eval/metrics.py` | TGFX metric functions |
| `src/eval/run.py` | TGFX fixture evaluation CLI |
| `src/eval/verify_sensor.py` | Deterministic sensor claim verifier |
| `src/eval/verify_llm.py` | Fixture-only judge interface |
| `src/features/vibration.py` | TGFX single vibration feature path seed |
| `src/common/config.py` | Pydantic config models and YAML loading |
| `src/common/schemas.py` | Pydantic row contracts and enums |
| `src/common/io_utils.py` | Parquet and JSON-list IO helpers |
| `src/common/ids.py` | Stable hash and ID helpers |
| `src/common/logging_utils.py` | Logger and run summary helpers |
| `src/etl/sensor_etl.py` | Sensor ingestion/windowing |
| `src/etl/text_etl.py` | Manual parsing/chunking |
| `src/etl/video_etl.py` | Video probing/normalization/indexing |
| `src/etl/assemble_incidents.py` | Incident assembly |
| `src/ui/incident_explorer.py` | UI data helpers |
| `streamlit_app.py` | Streamlit UI |
| `contracts/core.py` | TGFX core Pydantic contracts |
| `contracts/explanation.py` | TGFX explanation output contract |

## Entry Points

CLI:
- `python -m src.cli`.
- Console script in `pyproject.toml`: `recipe-a = "src.cli:app"`.

Web UI:
- `streamlit run streamlit_app.py`.

Tests:
- `pytest -q --cov=src --cov=contracts --cov-report=term-missing`.
TGFX fixture eval:
- `python -m src.eval.run --fixtures oracle`.
- `python -m src.eval.run --fixtures corrupted_intervals`.

## APIs

CLI commands:
- `sensor`
- `text`
- `video`
- `assemble`
- `all`
- `evaluate`

No REST API was found. Inference from absence of FastAPI/Flask dependencies and route code in current scans.

## Database Schema

No database is implemented. The project uses local Parquet contracts.

Current artifact schemas:
- `incidents.parquet`: `incident_id`, `source_dataset`, `machine_family`, `failure_family`, `window_start_s`, `window_end_s`, `fs_hz`, `sensor_file`, `sensor_channels`, `sensor_relevant_spans`, `video_file`, `video_fps`, `video_relevant_spans`, `sop_chunk_ids`, `maintenance_chunk_ids`, `phase_label`, `regime_label`, `severity_label`, `root_cause_label`, `alignment_method`, `split`.
- `sensor_windows.parquet`: `incident_id`, `source_dataset`, `machine_family`, `failure_family`, `window_start_s`, `window_end_s`, `fs_hz`, `sensor_file`, `sensor_channels`, `sensor_relevant_spans`, `n_samples`.
- `text_chunks.parquet`: `doc_id`, `chunk_id`, `doc_type`, `text`, `topic_tags`, `n_tokens`.
- `video_index.parquet`: `video_id`, `video_file`, `video_fps`, `duration_s`, `regime_label`, `condition_label`, `source`.

Evidence:
- Current pandas row-count/schema command.

## Models

Pydantic row models:
- `Span`
- `SensorWindowRow`
- `VideoIndexRow`
- `TextChunkRow`
- `IncidentRow`

TGFX contract models:
- `SensorWindow`
- `VideoClip`
- `SOPChunk`
- `TimelineEntry`
- `IncidentTuple`
- `AlignedTuple`
- `ChainClaim`
- `ExplanationOutput`

Enums:
- `FailureFamily`
- `Regime`
- `Condition`
- `DocType`
- `Severity`
- `Split`
- `AlignmentMethod`

Evidence:
- `src/common/schemas.py`.

## Services

No external service process is required beyond local Streamlit for UI. Inference based on source/config scan and successful local runtime.

## Configurations

Main config:
- `config/dataset.yaml`.

Important config groups:
- `paths`
- `sensor`
- `video`
- `text`
- `assemble`
- `runtime`

## Environment Variables

No required environment variables were found in source scan. Inference based on `docs/codebase_audit/01_repository_inventory.md` and current source structure.

## Third-Party Integrations

Python dependencies:
- `pydantic`, `pyyaml`, `pandas`, `pyarrow`, `numpy`, `scipy`, `typer`, `streamlit`, `tiktoken`, `pypdf`, `python-docx`, `rank-bm25`, `matplotlib`, `pytest`, `pytest-cov`.

External binary:
- `ffmpeg`/`ffprobe`; `ffmpeg -version` passes.
