# Codebase Inventory

## Purpose

Document what exists in the repository now: languages, folders, source modules, tests, docs, dependencies, configs, data paths, entry points, and operational commands.

## Repository Identity

| Item | Current Value |
|---|---|
| Project | CNC Multimodal Failure-Explanation Dataset Pipeline, "Recipe A" |
| Package name | `recipe-a-pipeline` |
| Primary language | Python |
| Main CLI module | `src.cli` |
| Main config | `config/dataset.yaml` |
| Final pipeline output | `data_processed/incidents.parquet` |
| Test framework | pytest |
| UI layer | None currently implemented |
| GPU layer | None currently implemented |

## Top-Level Folders

| Folder | Current Responsibility |
|---|---|
| `.github/workflows` | CI workflow |
| `config` | Pipeline YAML configuration |
| `docs` | Existing design, architecture, evaluation, and test docs |
| `docs/refactor_ecosystem` | Stage A generated documentation and plans |
| `notebooks` | Placeholder for notebooks; contains `.gitkeep` |
| `src` | Pipeline source code |
| `src/common` | Shared config, schemas, IO, logging, ids, errors |
| `src/etl` | Sensor, text, video, and incident assembly stages |
| `tests` | pytest tests and synthetic fixtures |

Expected but gitignored runtime folders:

| Folder | Purpose |
|---|---|
| `data_raw` | User-supplied raw sensor/video/text inputs |
| `data_processed` | Pipeline outputs |
| `logs` | Runtime logs |

## Source Modules

| Module | Current Role |
|---|---|
| `src/cli.py` | Typer CLI orchestration |
| `src/evaluate.py` | Dataset quality metrics and report rendering |
| `src/common/config.py` | Pydantic config models and YAML loader |
| `src/common/schemas.py` | Pydantic row schemas and controlled vocabularies |
| `src/common/io_utils.py` | JSON-list serialization, Parquet IO, path helpers, idempotency check |
| `src/common/logging_utils.py` | Structured logging and `RunSummary` |
| `src/common/ids.py` | Deterministic IDs |
| `src/common/errors.py` | Pipeline-specific exceptions |
| `src/etl/sensor_etl.py` | Sensor readers, normalization, fs estimation, event detection, windowing |
| `src/etl/text_etl.py` | Manual reading, tokenization, chunking, topic tagging |
| `src/etl/video_etl.py` | ffprobe/ffmpeg integration, normalization, tag merge |
| `src/etl/assemble_incidents.py` | Incident assembly, labels, video match, text retrieval, split assignment |

## Entry Points

| Entry Point | Command |
|---|---|
| CLI help | `python -m src.cli --help` |
| Sensor ETL | `python -m src.cli sensor --config config/dataset.yaml` |
| Text ETL | `python -m src.cli text --config config/dataset.yaml` |
| Video ETL | `python -m src.cli video --config config/dataset.yaml` |
| Assembly | `python -m src.cli assemble --config config/dataset.yaml` |
| Full pipeline | `python -m src.cli all --config config/dataset.yaml` |
| Evaluation | `python -m src.cli evaluate --config config/dataset.yaml --tier mvp` |
| Installed script | `recipe-a`, declared in `pyproject.toml` |

## Data Contracts

| Contract | Producer | Consumer |
|---|---|---|
| `data_processed/sensor_windows/*.parquet` | `SensorETL` | `IncidentAssembler`, `evaluate.py` |
| `data_processed/sensor_windows.parquet` | `SensorETL` | `IncidentAssembler`, `evaluate.py` |
| `data_processed/text_chunks.parquet` | `TextETL` | `IncidentAssembler`, `evaluate.py` |
| `data_processed/video/*.mp4` | `VideoETL` | `IncidentAssembler`, `evaluate.py` |
| `data_processed/video_index.parquet` | `VideoETL` | `IncidentAssembler`, `evaluate.py` |
| `data_processed/incidents.parquet` | `IncidentAssembler` | `evaluate.py`, downstream thesis modeling |
| `data_processed/eval_report.json` | `evaluate.py` | Review/acceptance tracking |
| `data_processed/eval_report.md` | `evaluate.py` | Human-readable evaluation |

## Existing Documentation

| Document | Status |
|---|---|
| `README.md` | Useful quickstart; lacks Streamlit/GPU notes and still references docs that are partly Phase 1 |
| `CONTRIBUTING.md` | Useful developer setup; no Streamlit/GPU section |
| `docs/recipe_a_overview.md` | Strong conceptual overview; still marked Phase 1 |
| `docs/implementation_plan.md` | Strong plan; still marked design/gated even though code exists |
| `docs/architecture.md` | Strong architecture doc; still says Phase 1/target Phase 2 in places |
| `docs/software_design.md` | Strong design doc; contains design sketches that now overlap with implementation |
| `docs/test_strategy_and_plan.md` | Good test plan; should be refreshed with current passing tests |
| `docs/test_cases.md` | Good test case catalog; aligns with test IDs |
| `docs/evaluation_criteria.md` | Good evaluation criteria; remains relevant |

## CI/CD

`.github/workflows/ci.yml` runs on push to `main`, pull requests, and manual dispatch. It tests Python 3.10, 3.11, 3.12, and 3.13, installs `requirements.txt`, runs advisory ruff lint, then runs pytest with coverage.

## Current Completeness

| Area | Current State |
|---|---|
| Core ETL | Implemented |
| CLI | Implemented |
| Evaluation | Implemented |
| Tests | Implemented and passing locally |
| Streamlit UI | Missing |
| GPU abstraction | Missing |
| Raw data staging | Not present in repo, expected manual step |
| Real video normalization validation | Blocked locally by missing ffmpeg |
| Documentation freshness | Needs refresh to match implementation |
