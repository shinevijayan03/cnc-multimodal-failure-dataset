# Repository Inventory

## Repository Baseline

Evidence:
- Branch: `main` from `git branch --show-current`.
- Commit: `c37bea9779f7c2d8d84a03078de74aebe5c70225` from `git rev-parse HEAD`.
- Working tree: dirty before audit docs were created. `git status --short` listed modified application/config/test files and untracked `streamlit_app.py`, `src/ui/`, `tests/unit/test_incident_explorer.py`, and `docs/refactor_ecosystem/`.

Inference:
- The dirty state appears to include prior implementation/refactor work. Evidence is only the git status; authorship is unknown.

## Project Type

| Area | Finding | Evidence |
|---|---|---|
| Language | Python | `pyproject.toml`, `requirements.txt`, `src/*.py`, `tests/*.py` |
| Runtime UI | Streamlit | `requirements.txt` includes `streamlit>=1.54`; `streamlit_app.py` imports `streamlit as st` |
| CLI framework | Typer | `requirements.txt` includes `typer>=0.9`; `src/cli.py` defines `app = typer.Typer(...)` |
| Data processing | pandas, pyarrow, numpy, scipy | `requirements.txt`; ETL modules import pandas/numpy/scipy-adjacent logic |
| Test framework | pytest and pytest-cov | `pyproject.toml` pytest config; `.github/workflows/ci.yml`; `pytest -q --cov=src` passed |
| Lint tool | ruff | `.github/workflows/ci.yml`; `ruff check src tests` passed |
| Build system | setuptools via pyproject | `pyproject.toml` has `[build-system]` with `setuptools>=68` |

## Top-Level Folders

| Path | Purpose | Evidence |
|---|---|---|
| `.github/workflows/` | CI workflow | `.github/workflows/ci.yml` runs dependency install, ruff, and pytest with coverage |
| `config/` | Runtime dataset configuration | `config/dataset.yaml` defines paths, ETL knobs, split config, logging |
| `data_pipeline/` | Raw data, processed data, and logs | `config/dataset.yaml` paths; observed `data_raw`, `data_processed`, `logs` |
| `docs/` | Project design and audit documentation | README "Design documents"; existing docs and this audit folder |
| `notebooks/` | Notebook placeholder | `notebooks/.gitkeep`; no executable notebook found in current file listing |
| `src/` | Application package | `src/cli.py`, `src/etl/*`, `src/common/*`, `src/ui/*`, `src/evaluate.py` |
| `tests/` | Unit and integration tests | `pytest --collect-only -q` found 87 tests |

## Important Files

| File | Purpose | Evidence |
|---|---|---|
| `README.md` | Quickstart, status, project explanation | Contains commands for install, CLI all/evaluate, Streamlit |
| `pyproject.toml` | Package metadata, dependency declarations, pytest and ruff config | Contains project name, dependencies, `recipe-a` script, pytest settings |
| `requirements.txt` | Runtime, optional, and dev dependency install list | Used by README and CI |
| `config/dataset.yaml` | Single source of truth for ETL inputs/outputs and tuning | Defines `paths`, `sensor`, `video`, `text`, `assemble`, `runtime` |
| `streamlit_app.py` | Web UI entry point | Imports `streamlit` and `src.ui.incident_explorer`; defines `main()` |
| `src/cli.py` | CLI entry point and stage orchestration | Typer commands `sensor`, `text`, `video`, `assemble`, `all`, `evaluate` |
| `src/evaluate.py` | Dataset metric and grade generation | Defines `compute_metrics`, `_grade`, `evaluate_build` |
| `.github/workflows/ci.yml` | CI baseline | Matrix Python 3.10 to 3.13, ruff advisory, pytest coverage required |

## Source Folders and Responsibilities

| Path | Responsibility | Evidence |
|---|---|---|
| `src/common/config.py` | Pydantic config models and YAML load/validation | Defines `PipelineConfig`, `PathsCfg`, `SensorCfg`, etc. |
| `src/common/schemas.py` | Pydantic row contracts and enums | Defines `SensorWindowRow`, `VideoIndexRow`, `TextChunkRow`, `IncidentRow` |
| `src/common/io_utils.py` | JSON-list handling, Parquet IO, path helpers | Defines `write_parquet_atomic`, `read_parquet`, `load_json_col` |
| `src/common/ids.py` | Stable deterministic IDs | Defines `incident_id`, `video_id`, `doc_id`, `chunk_id` |
| `src/common/logging_utils.py` | JSON/text logging and `RunSummary` | Defines `get_logger`, `RunSummary` |
| `src/etl/sensor_etl.py` | Sensor readers, normalization, event detection, windowing, sensor index output | Defines `SensorETL`, `EventDetector`, `WindowCarver` |
| `src/etl/text_etl.py` | Document reading, tokenization, chunking, topic tagging | Defines `TextETL`, `DocReader`, `Chunker`, `TopicTagger` |
| `src/etl/video_etl.py` | Video probing, normalization, tag merge, video index output | Defines `VideoETL`, `FfmpegNormalizer`, `FfprobeReader`, `TagMerger` |
| `src/etl/assemble_incidents.py` | Joins modality indexes into incident rows | Defines `IncidentAssembler`, `VideoMatcher`, `TextRetriever`, `SplitAssigner` |
| `src/ui/incident_explorer.py` | Streamlit helper layer for loading and presenting generated artifacts | Defines `load_pipeline_tables`, `artifact_status`, `alignment_rows` |

## Test Inventory

Evidence from `pytest --collect-only -q`:
- Total collected tests: `87`.
- Integration tests: `tests/integration/test_integration.py`, 15 collected tests.
- Unit tests cover assemble, config, incident explorer, IO/IDs, schemas, sensor, text, and video modules.
- Full suite result: `87 passed in 45.58s`.

## Data and Artifacts

| Path | Status | Evidence |
|---|---|---|
| `data_pipeline/data_raw/sensor_dataset` | Present | `Get-ChildItem -Recurse -Depth 2` showed raw input root |
| `data_pipeline/data_raw/text_manuals` | Present | Five manual files listed in text manuals folder |
| `data_pipeline/data_raw/video_raw` | Present | raw video root exists |
| `data_pipeline/data_processed/incidents.parquet` | Present | row count `1702`, cols `21` |
| `data_pipeline/data_processed/sensor_windows.parquet` | Present | row count `1702`, cols `11` |
| `data_pipeline/data_processed/text_chunks.parquet` | Present | row count `934`, cols `6` |
| `data_pipeline/data_processed/video_index.parquet` | Present | row count `20`, cols `7` |

## Environment Variables and Secrets

Finding:
- No required environment variables were found in source by `rg -n "os\.environ|os\.getenv|dotenv|SECRET|TOKEN|PASSWORD|API_KEY|DATABASE|sqlite|postgres|mysql|http://|https://" ...`.
- `src/common/io_utils.py` imports `os`, but no environment access was found by that scan.

Unknown:
- The audit did not inspect binary data files for secrets.

## External Services and Binaries

| Dependency | Evidence | Status |
|---|---|---|
| ffmpeg/ffprobe | `requirements.txt` notes external binary; `src/etl/video_etl.py` install hint; `ffmpeg -version` passed | Available |
| Streamlit local web server | `streamlit_app.py`; HTTP check to localhost passed | Available |
| No database service | No database dependency or connection string found | Inference from code/config scan |

## Generated or Cache Files

Observed generated/cache folders:
- `__pycache__/`, `src/**/__pycache__/`, `tests/**/__pycache__/`.
- `.pytest_cache/`.
- `.ruff_cache/`.
- `data_pipeline/data_processed/`.
- `data_pipeline/logs/`.
- `docs/codebase_audit/` from this audit.

