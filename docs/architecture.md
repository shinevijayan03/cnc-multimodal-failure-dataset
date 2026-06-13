# Architecture — Recipe A Pipeline

**Status:** Phase 1 (design). **Companion:** [Implementation Plan](implementation_plan.md)
· [Software Design](software_design.md).

This document describes the *system* shape: directory layout, dataflow from raw
files to `incidents.parquet`, the four ETL components, configuration management,
logging/monitoring, and CLI entrypoints.

---

## 1. Architectural style & principles

- **Batch, file-based ETL.** No services/DB. Inputs are files; outputs are
  Parquet indices + media files. Reproducible, inspectable, diff-able.
- **Staged & decoupled.** Four independent ETL stages communicate *only* through
  on-disk Parquet "contracts" (the indices). A stage can be re-run in isolation.
- **Config-as-contract.** [`config/dataset.yaml`](../config/dataset.yaml) is the
  single source of truth; code reads a typed view of it, never literals.
- **Schema-validated boundaries.** Every index row passes through a Pydantic
  model before write → bad data fails at the boundary, not three stages later.
- **Idempotent & atomic.** Stable ids + skip-if-exists + temp-file-then-rename.
- **Honest provenance.** Heuristic cross-modal links carry an `alignment_method`
  marker; nothing is presented as co-recorded ground truth.

---

## 2. Directory layout (target, Phase 2)

```
data_pipeline/
├── config/
│   └── dataset.yaml              # all knobs (single source of truth)
├── data_raw/                     # USER-SUPPLIED, gitignored
│   ├── bosch_cnc/  kaggle_cnc/  cnc_mill_tool_wear/
│   ├── multi_sensor_cnc/  milling_lifecycle/      # sensor datasets
│   ├── video_raw/   ├── *.mp4   └── video_tags.csv
│   └── text_manuals/  *.md | *.docx | *.txt
├── data_processed/               # PIPELINE OUTPUT, gitignored
│   ├── sensor_windows/<incident_id>.parquet   # per-incident waveforms
│   ├── sensor_windows.parquet    # ── index (Stage 1)
│   ├── video/<video_id>.mp4       # normalized clips
│   ├── video_index.parquet       # ── index (Stage 3)
│   ├── text_chunks.parquet        # ── index (Stage 2)
│   └── incidents.parquet          # ── FINAL join (Stage 4)
├── src/
│   ├── cli.py                    # Typer entrypoint (sensor|text|video|assemble|all)
│   ├── common/                   # shared infra (config, schemas, io, logging)
│   │   ├── config.py  schemas.py  io_utils.py  logging_utils.py  ids.py
│   ├── etl/
│   │   ├── sensor_etl.py  text_etl.py  video_etl.py  assemble_incidents.py
│   └── evaluate.py               # metrics report (Stage 7)
├── tests/ {unit, integration, fixtures}
├── notebooks/evaluate_dataset.ipynb
└── docs/  (this set)
```

---

## 3. End-to-end dataflow

```
   RAW (data_raw/, user-supplied)                PROCESSED (data_processed/)
   ───────────────────────────────               ─────────────────────────────────

   bosch_cnc/ kaggle_cnc/ ...  ─┐
   (CSV / H5 vibration logs)    │   ┌────────────────┐   sensor_windows/<id>.parquet
                                ├──►│  sensor_etl    ├──►  +  sensor_windows.parquet
                                │   └────────────────┘             │
                                │     normalize→fs→detect→window   │
                                                                   │
   text_manuals/*.md|docx ──────────►┌────────────┐               │
                                     │  text_etl  ├──► text_chunks.parquet
                                     └────────────┘               │
                                       parse→chunk→tag            │
                                                                  │
   video_raw/*.mp4 + tags.csv ──────►┌─────────────┐             │
                                     │  video_etl  ├──► video/*.mp4
                                     └─────────────┘   + video_index.parquet
                                       probe→normalize→tag        │
                                                                  │
                                                                  ▼
                              ┌───────────────────────────────────────────┐
                              │           assemble_incidents              │
                              │  for each sensor window:                  │
                              │   • derive/label  • match video (regime)  │
                              │   • retrieve SOP+maint chunks (topics)    │
                              │   • carry spans  • assign split           │
                              └───────────────────┬───────────────────────┘
                                                  ▼
                                        incidents.parquet  (DELIVERABLE)
                                                  │
                                                  ▼
                                    evaluate.py / notebook → metrics report
```

**Read it as:** three independent producers each emit one index; the consumer
(`assemble_incidents`) joins them by *label/topic relevance*, not by row-key —
because the modalities were never co-recorded.

---

## 4. Component descriptions

### 4.1 `sensor_etl`
- **Responsibility:** raw vibration logs → normalized → events → incident windows
  → `sensor_windows.parquet` + per-incident waveform files.
- **Key collaborators:** `Normalizer`, `FsEstimator`, `EventDetector`,
  `WindowCarver`, `EvidenceSpanExtractor` (see [Software Design](software_design.md)).
- **Contract out:** `SensorWindowRow` schema.
- **Failure isolation:** per-run try/except; one bad run does not abort the dataset
  unless `runtime.fail_fast`.

### 4.2 `text_etl`
- **Responsibility:** manuals → plain text → ~150–200-token chunks → topic tags →
  `text_chunks.parquet`.
- **Key collaborators:** `DocReader` (md/docx/txt), `Chunker`, `TopicTagger`.
- **Contract out:** `TextChunkRow` schema.

### 4.3 `video_etl`
- **Responsibility:** raw MP4 → probe → normalize (720p/30fps) → merge human tags
  → `video_index.parquet` + normalized clips.
- **Key collaborators:** `FfprobeReader`, `FfmpegNormalizer`, `TagMerger`.
- **Contract out:** `VideoIndexRow` schema.
- **External dependency:** `ffmpeg`/`ffprobe` on `PATH` (only this component).

### 4.4 `assemble_incidents`
- **Responsibility:** join the three indices into `incidents.parquet`.
- **Key collaborators:** `LabelDeriver`, `VideoMatcher`, `TextRetriever`,
  `SplitAssigner`.
- **Contract out:** `IncidentRow` schema (the deliverable).

### 4.5 `common/` (cross-cutting)
- `config.py` — load + validate YAML into typed `PipelineConfig`.
- `schemas.py` — Pydantic row models + enums (failure family, regime, …).
- `io_utils.py` — atomic Parquet read/write, JSON-list column (de)serialization,
  path resolution, skip-if-exists.
- `ids.py` — deterministic id generation (hash of source + offset) for idempotency.
- `logging_utils.py` — structured logger + per-stage run summary.

---

## 5. Configuration management

```
config/dataset.yaml ──► common.config.load_config() ──► PipelineConfig (pydantic)
                              │  validate types, ranges, required keys
                              │  resolve relative paths to absolute
                              ▼
        passed explicitly into every stage (no global singletons)
```

- **One file, typed view.** YAML is parsed once and validated into nested
  Pydantic models (`SensorConfig`, `VideoConfig`, `TextConfig`, `AssembleConfig`,
  `RuntimeConfig`). Code consumes attributes, never raw dict keys.
- **Versioned.** `config.version` is checked against a supported range.
- **Overridable** at the CLI: `--config <path>` and targeted `--set key=value`
  (Phase-2 nicety) for experiments without editing the file.
- **No secrets.** All inputs are local files; nothing requires credentials at run
  time (dataset acquisition is a manual, out-of-band step).

---

## 6. Logging & monitoring

- **Structured logging** (`runtime.log_format: json|text`, `log_level`). Each
  record carries `stage`, `dataset`/`file`, `event`, and counters.
- **Per-stage run summary** emitted at end: files seen / parsed / skipped,
  windows produced, chunks produced, clips normalized, rows written, wall time.
  This doubles as lightweight monitoring (compare runs across builds).
- **Provenance/quality counters** feed the evaluation report: missing files,
  malformed JSON, incidents lacking video/text, label coverage.
- **Logs** → `logs/<stage>-<timestamp>.log` + console. No external telemetry.
- **Determinism check (optional):** a `--manifest` mode writes a hash manifest of
  outputs so two runs can be diffed for reproducibility.

---

## 7. CLI entrypoints

```
python -m src.cli sensor    --config config/dataset.yaml [--limit N] [--dry-run]
python -m src.cli text      --config ...
python -m src.cli video     --config ...
python -m src.cli assemble  --config ...
python -m src.cli all       --config ...        # runs 1→2→3→4 in order
python -m src.cli evaluate  --config ...        # Stage 7 metrics report
```

- `--dry-run`: parse + validate inputs, log what *would* be written, write nothing.
- `--limit N`: cap items per stage for fast smoke runs (demo/M1).
- Exit codes: `0` success, non-zero on fatal config/IO error or (with
  `fail_fast`) first bad input. Missing-upstream errors name the command to run
  first (e.g. "run `sensor` before `assemble`").

---

## 8. Cross-cutting concerns

| Concern | Approach |
|---------|----------|
| **Reproducibility** | global `random_seed`; seeded video pick + split; deterministic ids |
| **Idempotency** | stable ids + skip-if-exists + atomic temp→rename writes |
| **Scalability** | per-file streaming; `runtime.num_workers` for embarrassingly-parallel stages (Phase 2+); caps to bound memory/disk |
| **Extensibility** | new sensor format = new `reader` + `column_map` (no core change); new retrieval = swap `TextRetriever` strategy |
| **Portability** | pure-Python + pyarrow + ffmpeg; Windows-first (author env) but POSIX-safe paths via `pathlib` |
| **Data safety** | `data_raw`/`data_processed` gitignored; `--dry-run`; never auto-download or overwrite raw |

---

## 9. Why these choices (key trade-offs)

- **Parquet indices over a database.** Zero infra, typed, columnar, pandas/pyarrow
  native, trivially shareable for a thesis. Cost: no concurrent writers — fine for
  batch.
- **Relevance-join over key-join across modalities.** The modalities are not
  co-recorded; a relevance/label join is the *honest* operation and is recorded
  as heuristic. Cost: assembly quality depends on label coverage (tracked in eval).
- **Per-incident waveform files + a slim index.** Keeps the index light and
  query-able; heavy time-series stay in addressable side files.
- **ffmpeg via subprocess (not a Python video lib).** Robust, ubiquitous, handles
  codecs/containers; isolates a heavy native dep to one stage.
- **Pydantic at boundaries.** Cheap insurance: schema drift and bad rows fail
  loudly and early, which matters for a multi-stage pipeline feeding a thesis.
