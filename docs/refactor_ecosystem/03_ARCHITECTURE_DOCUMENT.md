# Architecture Document

## Purpose

Describe the current architecture and the target architecture for completing the CNC multimodal failure-explanation dataset pipeline.

## 7.1 Executive Architecture Summary

The current system is a local batch ETL pipeline. It reads manually staged raw CNC sensor, text, and video files; writes validated Parquet contracts; assembles sensor-anchored multimodal incident rows; and evaluates dataset quality.

The architecture is intentionally file-based. There is no database, web service, queue, or remote API dependency. This fits the thesis context: the dataset must be reproducible, inspectable, and runnable on a workstation.

The main architectural gap is not the ETL core. The core is implemented and covered by tests. The missing completion layers are:

- A Streamlit UI for user-facing operation and diagnostics
- A GPU abstraction for any approved model/embedding acceleration
- Documentation refresh so all docs describe current implementation accurately
- Environment hardening around optional dependencies and ffmpeg
- Scale validation with real staged raw data

## 7.2 Current Architecture

Current architecture facts:

- The CLI is the primary user interface.
- `config/dataset.yaml` is loaded into Pydantic models.
- Each ETL stage receives a typed `PipelineConfig`.
- Stages communicate through Parquet files in `data_processed`.
- Pydantic models validate row contracts before writes.
- Atomic Parquet writes reduce partial-file risk.
- Deterministic IDs support reproducible reruns.
- Evaluation is a pure metrics layer over generated indices.

See: `docs/refactor_ecosystem/diagrams/current_architecture.mmd`

## 7.3 Target Architecture

Target architecture after approved Stage B:

- Preserve the file-based ETL core and Parquet contracts.
- Add a thin application service/orchestrator layer shared by CLI and Streamlit.
- Add a Streamlit UI as an operational layer, not a business-logic container.
- Add a diagnostics panel for config, raw-data presence, ffmpeg, optional deps, tests, and GPU status.
- Add a small compute-device utility only where GPU acceleration is useful.
- Refresh top-level docs and config comments to match current code.
- Add test coverage for UI and any GPU path introduced.

See: `docs/refactor_ecosystem/diagrams/target_architecture.mmd`

## 7.4 Component Breakdown

| Component | Current Location | Responsibility | Inputs | Outputs | Dependencies | Refactor Needed |
|---|---|---|---|---|---|---|
| CLI | `src/cli.py` | Run stages and evaluation from terminal | CLI args, config path | Exit codes, summaries | Typer, ETL modules | Minor: share runner with Streamlit |
| Config | `src/common/config.py` | Validate YAML and resolve paths | `dataset.yaml` | `PipelineConfig` | pydantic, pyyaml | Minor: more strategy validation |
| Schemas | `src/common/schemas.py` | Define row contracts | Row fields | Validated models | pydantic | No major refactor |
| IO | `src/common/io_utils.py` | Serialize list fields, read/write Parquet, atomic writes | Models/DataFrames/paths | Parquet files | pandas, pyarrow | No major refactor |
| Logging | `src/common/logging_utils.py` | Structured logs and summaries | Runtime config | Logger, `RunSummary` | stdlib logging | Optional file logging |
| Sensor ETL | `src/etl/sensor_etl.py` | Sensor normalization, event detection, windows | CSV/H5 sensor files | Sensor windows and index | pandas, numpy, optional h5py | Medium: output-format/config alignment |
| Text ETL | `src/etl/text_etl.py` | Manual reading, chunking, topic tagging | md/txt/docx/pdf | Text chunks index | optional tiktoken, pypdf, docx | Medium: dependency/docs alignment |
| Video ETL | `src/etl/video_etl.py` | Probe/normalize clips, merge tags | MP4s, tag CSV | Video index and normalized clips | ffmpeg/ffprobe | Medium: diagnostics and docs |
| Assembly | `src/etl/assemble_incidents.py` | Join modality contracts into incidents | Sensor/text/video indices | `incidents.parquet` | pandas, numpy | Medium: retrieval strategy alignment |
| Evaluation | `src/evaluate.py` | Compute metrics and render reports | Indices and config | eval reports | pandas | Medium: malformed JSON hardening |
| Streamlit UI | Proposed `streamlit_app.py` or `src/ui/streamlit_app.py` | User-facing run/diagnostic interface | Config, files, user controls | UI results, downloads | streamlit | Missing |
| Device utility | Proposed `src/common/device.py` or `src/utils/device.py` | CPU/GPU selection | prefer_gpu flag | device metadata | torch optional | Missing |

## 7.5 Runtime Flow

1. User runs a CLI command such as `python -m src.cli all --config config/dataset.yaml`.
2. CLI loads `dataset.yaml`.
3. Config loader validates schema version and Pydantic field constraints.
4. Config loader resolves `paths.*` values to absolute paths.
5. Sensor stage reads enabled datasets, normalizes channels/time, estimates sample rate, detects events, carves windows, and writes sensor contracts.
6. Text stage reads manuals, extracts text, chunks, topic-tags, and writes the text contract.
7. Video stage discovers MP4s, checks ffmpeg/ffprobe, normalizes or skips, merges tags, and writes the video contract.
8. Assembly stage reads modality contracts, derives labels, matches video, retrieves text chunks, assigns splits, and writes `incidents.parquet`.
9. Evaluation stage computes metrics and writes reports.

See: `docs/refactor_ecosystem/diagrams/runtime_flow.mmd`

## 7.6 Data Flow

Data enters through manually staged files in `data_raw` and configuration in `config/dataset.yaml`.

Intermediate outputs are Parquet files in `data_processed`. The sensor stage also writes one waveform Parquet file per incident window. JSON-list fields are stored as JSON strings in flat Parquet columns and decoded by shared IO helpers.

Final output is `data_processed/incidents.parquet`, which references sensor files, optional video files, SOP chunk IDs, maintenance chunk IDs, labels, evidence spans, and split assignments.

See: `docs/refactor_ecosystem/diagrams/data_flow.mmd`

## 7.7 Integration Points

| Integration | Type | Current Status |
|---|---|---|
| Raw sensor files | Local files | Expected under `data_raw/<dataset>` |
| Raw manuals | Local files | Expected under `data_raw/text_manuals` |
| Raw video clips | Local files | Expected under `data_raw/video_raw` |
| Video tags | CSV | Expected at `data_raw/video_raw/video_tags.csv` |
| ffmpeg/ffprobe | External binaries | Missing locally |
| PyTorch GPU | Optional environment capability | Available locally, unused by project |
| TensorFlow GPU | Optional environment capability | TensorFlow installed but no GPU visible |
| CI | GitHub Actions | Present |
| Streamlit | UI framework | Installed locally but unused/not declared |

No external APIs, databases, vector stores, or cloud services are currently used.

## 7.8 Deployment View

### CLI Execution

```bash
python -m src.cli all --config config/dataset.yaml
```

### Streamlit Execution

Current: not implemented.

Target:

```bash
streamlit run streamlit_app.py
```

or:

```bash
streamlit run src/ui/streamlit_app.py
```

### GPU-Enabled Execution

Current: not implemented by project code.

Target: use a config/UI flag such as `prefer_gpu` for approved embedding/model workloads. Log selected device and fall back to CPU if CUDA is unavailable.

### CPU Fallback Execution

Current pipeline is CPU-based and passes tests. CPU should remain the default fallback.

## 7.9 Risks and Gaps

| Risk/Gaps | Severity | Notes |
|---|---|---|
| No raw data staged | High | Cannot produce real `incidents.parquet` from repo config |
| ffmpeg missing | Medium | Video ETL gracefully skips, but video normalization cannot be validated |
| Docs/config stale | Medium | Phase 1 comments conflict with implemented Stage 2 code |
| No Streamlit UI | Medium | User-facing interface requirement not satisfied |
| No GPU abstraction | Medium | GPU requirement not satisfied where relevant |
| Retrieval method mismatch | Medium | Config says BM25, implementation uses topic-overlap ranking |
| Optional dependencies missing | Low/Medium | Text and retrieval behavior degrades |
| Lint cleanup | Low | 8 advisory findings |

## 7.10 Refactoring Recommendations

Priority order after approval:

1. Refresh README, CONTRIBUTING, config comments, and existing docs to reflect current implementation.
2. Add a shared pipeline runner/diagnostics service used by CLI and Streamlit.
3. Implement Streamlit UI for configuration inspection, stage execution, diagnostics, outputs, and evaluation reports.
4. Add device utility and optional GPU path only for meaningful workloads, most likely embedding retrieval.
5. Resolve retrieval strategy mismatch by implementing BM25 or renaming the config method.
6. Install/document ffmpeg and optional dependencies for full local capability.
7. Fix lint issues and add UI/GPU tests.
