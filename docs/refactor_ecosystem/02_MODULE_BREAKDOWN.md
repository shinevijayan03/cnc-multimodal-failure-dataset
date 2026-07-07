# Module Breakdown

## Purpose

Explain module decomposition, responsibilities, entry points, internal APIs, data flow, coupling, and refactoring needs.

## High-Level Decomposition

The system is a local, file-based ETL pipeline. It has three independent modality producers, one assembly consumer, and one evaluator.

| Layer | Modules | Responsibility |
|---|---|---|
| Interface | `src.cli` | Expose run commands and exit codes |
| Shared infrastructure | `src.common.*` | Config, schemas, IO, logging, ids, errors |
| ETL producers | `src.etl.sensor_etl`, `src.etl.text_etl`, `src.etl.video_etl` | Produce modality-specific Parquet contracts |
| Joiner | `src.etl.assemble_incidents` | Produce `incidents.parquet` |
| Evaluation | `src.evaluate` | Compute quality metrics and reports |
| Tests | `tests/*` | Unit, integration, CLI, and e2e smoke coverage |

## Significant Modules

| Module | Major Units | Inputs | Outputs | Refactor Needed |
|---|---|---|---|---|
| `src.cli` | Typer commands, `_load`, `_run_stage` | CLI args, config file | Exit codes, printed summaries | Minor: remove unused `log`; future: call service layer shared with Streamlit |
| `src.common.config` | `PipelineConfig`, nested config models, `load_config` | YAML | Typed config with resolved paths | Minor: validate more enum-like strategy values; document resolved paths |
| `src.common.schemas` | Row models and enums | Row dictionaries | Validated models | Low: keep current |
| `src.common.io_utils` | JSON-list helpers, Parquet IO, freshness check | DataFrames, models, paths | Parquet files and records | Low: keep current |
| `src.common.logging_utils` | JSON/text logger, `RunSummary` | Runtime config | Logs and summaries | Medium: optional file logging if `logs_dir` is meant to be used |
| `src.common.ids` | Stable hash/id functions | Source identifiers | Stable IDs | Low: keep current |
| `src.common.errors` | Exception hierarchy | Errors | Pipeline-specific exceptions | Low: keep current |
| `src.etl.sensor_etl` | Readers, `Normalizer`, `FsEstimator`, `EventDetector`, `WindowCarver`, `EvidenceSpanExtractor`, `SensorETL` | Raw sensor files, config | Sensor windows and index | Medium: reader registry validation; output format config alignment; optional batch/GPU benchmarking |
| `src.etl.text_etl` | Tokenizers, `DocReader`, `Chunker`, `TopicTagger`, `TextETL` | Manuals | Text chunks index | Medium: PDF/tiktoken dependency docs; retrieval alignment |
| `src.etl.video_etl` | `FfprobeReader`, `FfmpegNormalizer`, `TagMerger`, `VideoETL` | MP4s, tag CSV | Normalized clips and video index | Medium: ffmpeg installation validation; duration policy |
| `src.etl.assemble_incidents` | `LabelDeriver`, `VideoMatcher`, `TextRetriever`, `SplitAssigner`, `IncidentAssembler` | Sensor/text/video indices | Incidents index | Medium: BM25 method mismatch; metadata-driven labels |
| `src.evaluate` | `MetricsReport`, `compute_metrics`, `_grade`, `render_report`, `evaluate_build` | Incidents and indices | Metrics reports | Medium: harden malformed JSON counting; add plots if promised |

## Entry Points

| Entry | Calls |
|---|---|
| `python -m src.cli sensor` | `load_config` -> `SensorETL.run` |
| `python -m src.cli text` | `load_config` -> `TextETL.run` |
| `python -m src.cli video` | `load_config` -> `VideoETL.run` |
| `python -m src.cli assemble` | `load_config` -> `IncidentAssembler.run` |
| `python -m src.cli all` | Sensor -> Text -> Video -> Assemble |
| `python -m src.cli evaluate` | `evaluate_build` |

## Internal APIs

| API | Type | Used By |
|---|---|---|
| `PipelineConfig.resolve` | Path helper | ETL and evaluation modules |
| `RunSummary` | Stage result object | CLI and tests |
| Pydantic row models | Validation boundary | ETL producers and assembler |
| `rows_to_df` | Model to DataFrame bridge | All producers |
| `write_parquet_atomic` | IO boundary | All file-writing stages |
| `load_json_col` | JSON-list parser | Assembly and evaluation |
| `incident_id`, `video_id`, `chunk_id` | Deterministic ID generation | Sensor, video, text |

## Data Flow

1. Raw sensor data is normalized to canonical channels and time.
2. Sensor RMS/event detection identifies events.
3. Sensor windows are carved and written as per-incident Parquet files.
4. Text manuals are converted to plain text, chunked, tagged, and indexed.
5. Video clips are probed, optionally normalized with ffmpeg, tagged, and indexed.
6. Assembly reads the three modality indices, attaches video and text by heuristic relevance, derives labels, assigns splits, and writes `incidents.parquet`.
7. Evaluation reads the generated contracts and writes quality reports.

## Dependency Direction

Dependencies flow inward from CLI/ETL to shared infrastructure. The shared `common` modules do not depend on ETL modules, which keeps circular dependencies out of the current source.

No source-level cyclic dependency was identified.

## Coupling Hotspots

| Hotspot | Why It Matters | Recommendation |
|---|---|---|
| `IncidentAssembler` knows column names from all upstream indices | Schema drift could break assembly | Centralize column contract notes or add schema contract tests |
| `TextRetriever` behavior is configured as BM25 but implemented as overlap ranking | Scientific/retrieval expectations may drift | Implement BM25 or rename the method |
| `VideoETL` depends on external ffmpeg availability | Local builds differ by machine | Add diagnostics and setup docs |
| `config/dataset.yaml` is large and comments are stale | Users may trust incorrect comments | Refresh config comments after approval |
| CLI directly instantiates stages | Streamlit would duplicate orchestration | Introduce a thin service/orchestrator function shared by CLI and UI |

## Duplicated or Fragile Logic

- Path construction for output-relative paths appears in sensor and video stages. It is working, but a helper could reduce drift.
- JSON-list handling is centralized, which is good.
- Some docs duplicate architecture and design content; Stage B should refactor docs into current-state vs historical-design sections.

## Missing Abstractions

| Proposed Abstraction | Why |
|---|---|
| `src/services/pipeline_runner.py` or similar | Shared orchestration for CLI and future Streamlit UI |
| `src/utils/device.py` or `src/common/device.py` | CPU/GPU selection and logging if GPU work is approved |
| Retrieval strategy interface | Align config method names with actual retrieval implementations |
| Diagnostics service | Streamlit and CLI can share environment checks for ffmpeg, optional deps, and GPU |
