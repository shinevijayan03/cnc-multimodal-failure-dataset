# Software Design Document

## Purpose

Define the current module-level design and recommended target design for completing the pipeline without disrupting working behavior.

## 1. Design Goals

- Preserve the tested ETL core.
- Keep all behavior config-driven.
- Keep row contracts explicit and validated.
- Maintain deterministic output IDs and splits.
- Keep UI logic separate from ETL logic.
- Add GPU support only behind clear CPU fallback.
- Improve docs and diagnostics before large behavior changes.

## 2. Non-Goals

- Do not auto-download licensed datasets.
- Do not introduce a database unless a future scale requirement demands it.
- Do not move existing ETL logic wholesale into Streamlit.
- Do not force GPU use for small CPU-suitable Pandas/NumPy operations.
- Do not rewrite the architecture into services or cloud infrastructure.

## 3. Module Design

## Module: `src.cli`

### Current Responsibility

Expose Typer commands for `sensor`, `text`, `video`, `assemble`, `all`, and `evaluate`.

### Problems Observed

- `run_all()` assigns `log` but does not use it.
- CLI directly instantiates stages; future Streamlit UI would duplicate orchestration unless a shared runner is added.

### Target Responsibility

Remain a thin terminal adapter over shared pipeline-runner functions.

### Public Interfaces

- `app`
- command functions
- `main()`

### Inputs

CLI args and config path.

### Outputs

Exit codes and human-readable summaries.

### Dependencies

Typer, config loader, ETL stages, evaluator.

### Refactoring Actions

- Remove unused local variable.
- Add shared runner module after approval.
- Route CLI commands through the shared runner.

### Tests Required

Existing CLI tests plus runner tests for success/failure summaries.

## Module: `src.common.config`

### Current Responsibility

Parse YAML, validate into nested Pydantic models, check schema version, and resolve paths.

### Problems Observed

- Some strategy fields are plain strings with incomplete validation.
- Config comments are stale, but code is functioning.

### Target Responsibility

Continue as the single typed configuration boundary. Add validation for strategy enums and optional UI/GPU fields only when implemented.

### Public Interfaces

- `PipelineConfig`
- nested config models
- `load_config(path)`

### Inputs

YAML file.

### Outputs

Validated `PipelineConfig`.

### Dependencies

pydantic, pyyaml.

### Refactoring Actions

- Validate `threshold_kind`, retrieval method, video strategy, output format.
- Add optional `ui` and `compute` sections only if Stage B implements those features.

### Tests Required

Config validation tests for new fields and invalid strategies.

## Module: `src.common.schemas`

### Current Responsibility

Define row models and enums for sensor, video, text, and incident contracts.

### Problems Observed

No major issue. JSON-list fields are handled centrally.

### Target Responsibility

Remain the contract authority. Add new fields only through controlled schema changes.

### Public Interfaces

Pydantic row classes, enums, `JSON_LIST_FIELDS`.

### Tests Required

Round-trip and validation tests for any schema addition.

## Module: `src.common.io_utils`

### Current Responsibility

Serialize JSON-list fields, convert Pydantic models to records, perform atomic Parquet writes, read Parquet, resolve paths, and check freshness.

### Problems Observed

No major issue.

### Target Responsibility

Remain IO boundary. Consider a helper for repo-relative output paths if duplication grows.

### Tests Required

Existing IO tests should remain; add path helper tests if introduced.

## Module: `src.common.logging_utils`

### Current Responsibility

Configure JSON/text console logging and expose `RunSummary`.

### Problems Observed

`logs_dir` exists in config, but the logger currently writes to stderr only.

### Target Responsibility

Provide consistent console logs and optionally file logs if UI/diagnostics need them.

### Refactoring Actions

- Consider adding optional file handler controlled by config.
- Keep `RunSummary` stable for tests and UI display.

### Tests Required

Logger formatting and RunSummary rendering tests if changed.

## Module: `src.etl.sensor_etl`

### Current Responsibility

Read sensor files, normalize channels and time, estimate sampling frequency, detect events, carve windows, extract evidence spans, and write sensor contracts.

### Problems Observed

- `sensor.output_format` config mentions Parquet/HDF5, but implementation writes Parquet only.
- `runtime.num_workers` is not used.
- Current event detector is CPU NumPy/Pandas; GPU is not useful until scale/benchmark proves need.

### Target Responsibility

Remain the sensor backbone. Keep numeric core pure and testable.

### Public Interfaces

- `SensorETL.run`
- `READERS`
- `Normalizer`
- `FsEstimator`
- `EventDetector`
- `WindowCarver`
- `EvidenceSpanExtractor`

### Inputs

Raw CSV/H5 runs and sensor config.

### Outputs

Per-window Parquet files and `sensor_windows.parquet`.

### Dependencies

pandas, numpy, optional h5py.

### Refactoring Actions

- Either enforce Parquet in config validation or implement HDF5 output.
- Add diagnostics for missing dataset roots.
- Benchmark before adding any GPU path.

### Tests Required

Existing sensor tests plus any new output-format/config diagnostics tests.

## Module: `src.etl.text_etl`

### Current Responsibility

Read documents, tokenize, chunk, classify doc type, topic-tag, and write `text_chunks.parquet`.

### Problems Observed

- Optional dependencies missing locally: `tiktoken`, `pypdf`.
- PDF support exists in code/config, but depends on optional package.

### Target Responsibility

Remain document ingestion and chunking layer. If embeddings are approved, keep embedding generation in a separate service or strategy.

### Public Interfaces

- `TextETL.run`
- `DocReader`
- `Chunker`
- `TopicTagger`
- `make_tokenizer`

### Inputs

Manuals in md/txt/docx/pdf formats.

### Outputs

`text_chunks.parquet`.

### Dependencies

Optional tiktoken, pypdf, python-docx.

### Refactoring Actions

- Add clearer dependency diagnostics.
- Add optional embedding strategy only after approval.

### Tests Required

Existing text tests plus optional dependency diagnostics and embedding CPU/GPU fallback tests if implemented.

## Module: `src.etl.video_etl`

### Current Responsibility

Discover MP4 files, probe with ffprobe, normalize with ffmpeg, merge tags, and write video contracts.

### Problems Observed

- ffmpeg is missing locally.
- Duration out-of-range clips are only counted, not surfaced to users beyond summary notes.

### Target Responsibility

Keep external video tooling isolated and testable. Surface ffmpeg status clearly in Streamlit diagnostics.

### Public Interfaces

- `VideoETL.run`
- `FfprobeReader`
- `FfmpegNormalizer`
- `TagMerger`
- `parse_probe`

### Tests Required

Existing video tests plus real ffmpeg integration when ffmpeg is installed.

## Module: `src.etl.assemble_incidents`

### Current Responsibility

Read upstream contracts, derive labels, match video, retrieve text chunks, assign splits, validate and write incidents.

### Problems Observed

- Config says `keyword_bm25`, but `TextRetriever` currently ranks by topic overlap and token count.
- `Split.train` is used as a temporary placeholder before assignment; this is valid but should be documented.
- Labels are mostly defaults unless upstream metadata improves.

### Target Responsibility

Remain the cross-modal joiner. Isolate retrieval and matching strategies.

### Public Interfaces

- `IncidentAssembler.run`
- `LabelDeriver`
- `VideoMatcher`
- `TextRetriever`
- `SplitAssigner`

### Inputs

Sensor, text, and optional video indices.

### Outputs

`incidents.parquet`.

### Refactoring Actions

- Implement actual BM25 or rename method to `topic_overlap`.
- Add explicit strategy classes if retrieval grows.
- Improve label derivation from available dataset metadata.

### Tests Required

Existing assembly tests plus BM25/topic-overlap strategy tests.

## Module: `src.evaluate`

### Current Responsibility

Load indices, compute metrics, grade build, and write JSON/Markdown reports.

### Problems Observed

- Comment says malformed JSON decode would raise; malformed JSON percentage is hard-coded to 0 after decoding succeeds.
- Evaluation fails if `incidents.parquet` is absent, which is expected but should be surfaced in UI diagnostics.

### Target Responsibility

Remain evaluation service. Harden malformed JSON reporting and add optional plot artifacts only if documented.

### Tests Required

Existing evaluation tests plus malformed JSON parsing behavior if changed.

## Module: Proposed Streamlit UI

### Current Responsibility

Missing.

### Target Responsibility

Provide a local UI for:

- Config selection and inspection
- Raw data readiness checks
- Stage execution controls
- CPU/GPU preference where relevant
- Progress/status summaries
- Evaluation report display
- Output download links
- Diagnostics for optional dependencies, ffmpeg, and GPU

### Recommended Location

Use `streamlit_app.py` at repo root for simple launch:

```bash
streamlit run streamlit_app.py
```

If Stage B adds a deeper UI package, use `src/ui/streamlit_app.py` and document:

```bash
streamlit run src/ui/streamlit_app.py
```

### Tests Required

At minimum, import smoke tests for UI helper functions and service-level tests for actions invoked by the UI.

## Module: Proposed GPU Utility

### Current Responsibility

Missing.

### Target Responsibility

Centralize CPU/GPU detection:

```python
def get_compute_device(prefer_gpu: bool = True) -> dict:
    ...
```

Return device type, name, availability, reason for fallback, and library details. Avoid importing heavy GPU libraries unless the feature needs them.

### Tests Required

Mock CUDA available/unavailable paths and confirm CPU fallback.

## 4. Data Contracts

| Data Model | Storage | Producer |
|---|---|---|
| `SensorWindowRow` | `sensor_windows.parquet` | Sensor ETL |
| `VideoIndexRow` | `video_index.parquet` | Video ETL |
| `TextChunkRow` | `text_chunks.parquet` | Text ETL |
| `IncidentRow` | `incidents.parquet` | Incident assembly |

## 5. Error Handling Strategy

Current strategy should remain:

- Config errors abort with explicit key names.
- Per-file/run failures are logged and counted unless `fail_fast` is enabled.
- External video tool failures are isolated to the video stage.
- Missing sensor upstream fails assembly with an actionable command.
- Invalid rows are skipped rather than written.

## 6. Logging Strategy

Current console JSON/text logging is acceptable. Stage B should decide whether to write log files under `logs_dir` and expose recent logs in Streamlit.

## 7. Configuration Strategy

`dataset.yaml` remains the source of truth. New UI/GPU settings should be optional and backwards-compatible.

## 8. Streamlit UI Design

Keep Streamlit as a thin interface over backend services. Heavy ETL logic stays in source modules.

## 9. GPU Abstraction Design

Add GPU support only for approved workloads such as embeddings or model inference. Do not move current Pandas ETL to GPU without benchmark evidence.

## 10. Testing Hooks

Use existing pure units as the model: keep new services injectable, deterministic, and testable without raw licensed data.

## 11. Extension Points

- New sensor readers via `READERS`
- New text tokenizers/taggers
- New retrieval strategy
- New video match strategy
- New evaluation metrics
- New UI pages using shared services

## 12. File/Folder Ownership

| Path | Owner |
|---|---|
| `src/common` | Shared infrastructure |
| `src/etl` | ETL stages |
| `src/evaluate.py` | Metrics/evaluation |
| `src/cli.py` | CLI adapter |
| `streamlit_app.py` or `src/ui` | Proposed UI adapter |
| `tests` | Unit/integration validation |
| `docs` | User/developer documentation |
| `docs/refactor_ecosystem` | Stage A planning and audit artifacts |
