# 03 — Current Architecture Map

All elements below exist in code (paths cited). Nothing is invented; dashed
notes call out declared-but-unimplemented aspects.

## 1. Component diagram

```mermaid
graph LR
  subgraph Config
    Y[config/dataset.yaml] --> C[src/common/config.py<br/>typed PipelineConfig]
  end

  subgraph ETL["ETL stages (src/etl)"]
    S[sensor_etl.py<br/>readers → Normalizer → FsEstimator →<br/>EventDetector → WindowCarver →<br/>EvidenceSpanExtractor]
    T[text_etl.py<br/>DocReader → Chunker → TopicTagger]
    V[video_etl.py<br/>FfprobeReader → FfmpegNormalizer → TagMerger]
    A[assemble_incidents.py<br/>LabelDeriver + VideoMatcher +<br/>TextRetriever + SplitAssigner]
  end

  CLI[src/cli.py<br/>Typer: sensor,text,video,assemble,all,evaluate] --> S & T & V & A
  C --> CLI
  S --> SW[(sensor_windows.parquet<br/>+ per-incident waveforms)]
  T --> TC[(text_chunks.parquet)]
  V --> VI[(video_index.parquet)]
  SW & TC & VI --> A --> INC[(incidents.parquet)]

  INC --> E[src/evaluate.py<br/>quality metrics, PASS/WARN/FAIL]
  INC --> TG[src/tgfx/dataset.py<br/>manifest + ledger + splits]
  INC --> UI[streamlit_app.py +<br/>src/ui/incident_explorer.py]

  subgraph TGFX_eval["TGFX eval substrate"]
    K[contracts/ core + explanation]
    M[src/eval/metrics.py]
    F[src/eval/fixtures.py]
    VS[src/eval/verify_sensor.py]
    VL[src/eval/verify_llm.py<br/>placeholder judge]
    R[src/eval/run.py → docs/_eval/runs.jsonl]
    FEAT[src/features/vibration.py<br/>rms, variance, kurtosis, rose]
    F --> M --> R
    K --> M
    FEAT --> VS --> M
    VL -.fixture-only.-> M
  end
```

## 2. Data flow diagram

```mermaid
flowchart LR
  RAWS[data_raw/sensor_dataset<br/>CSV runs, 2 kHz, ax/ay/az] --> S1[normalize + synth time_s]
  S1 --> S2[RMS event detection<br/>quantile 0.80]
  S2 --> S3[carve ±8 s windows<br/>t_rel_s incident-relative]
  S3 --> S4[threshold-crossing<br/>evidence spans]
  S4 --> SWP[(sensor_windows.parquet)]

  RAWT[data_raw/text_manuals<br/>PDF/MD SOP + maintenance] --> T1[extract + chunk<br/>~175 tokens, heading-aware]
  T1 --> T2[keyword topic tags] --> TCP[(text_chunks.parquet)]

  RAWV[data_raw/video_raw<br/>MP4 + video_tags.csv] --> V1[ffmpeg normalize<br/>720p/30fps/5-10 s] --> VIP[(video_index.parquet)]

  SWP & TCP & VIP --> J[join: weak labels →<br/>video label-match →<br/>keyword chunk retrieval →<br/>grouped split]
  J --> IP[(incidents.parquet<br/>1702 rows)]
  IP --> Q[eval_report.json/md<br/>GRADE: PASS]
  IP --> MAN[manifest.json + alignment_ledger.jsonl<br/>+ data/splits/*.jsonl]
  IP --> APP[Streamlit explorer]
```

## 3. Runtime flow diagram

```mermaid
sequenceDiagram
  participant U as User
  participant CLI as src/cli.py
  participant St as Stage (SensorETL/TextETL/VideoETL/Assembler)
  participant P as data_processed/

  U->>CLI: python -m src.cli all --config config/dataset.yaml
  CLI->>CLI: load_config() → PipelineConfig (pydantic)
  loop sensor → text → video
    CLI->>St: stage.run(limit, dry_run)
    St->>P: write_parquet_atomic(index)
    St-->>CLI: RunSummary (ok, counts)
  end
  CLI->>St: IncidentAssembler.run()
  St->>P: incidents.parquet
  U->>CLI: python -m src.cli evaluate --tier mvp
  CLI->>P: read indices → metrics → eval_report.{json,md}
  U->>U: streamlit run streamlit_app.py (browse incidents)
```

## 4. Module dependency map

```mermaid
graph TD
  cli --> common.config & etl.sensor_etl & etl.text_etl & etl.video_etl & etl.assemble_incidents & evaluate
  etl.sensor_etl --> common.config & common.errors & common.ids & common.io_utils & common.logging_utils & common.schemas
  etl.assemble_incidents --> common.schemas & common.io_utils
  evaluate --> common.config & common.io_utils
  tgfx.dataset --> common.config & common.io_utils
  ui.incident_explorer --> common.io_utils
  eval.metrics --> contracts & eval.fixtures & eval.verify_sensor
  eval.verify_sensor --> eval.fixtures & features.vibration
  eval.run --> eval.fixtures & eval.metrics
  scripts.build_dataset --> tgfx.dataset
```

Notable: `src/eval/` and `contracts/` do **not** depend on `src/etl/` — the TGFX
eval substrate is decoupled from the dataset pipeline and currently connects
only through hand-authored fixtures, not real pipeline outputs.

## 5. Storage / data model map

| Store | Format | Row model | Producer |
|---|---|---|---|
| `sensor_windows.parquet` | parquet index | `SensorWindowRow` | sensor_etl |
| `sensor_windows/*.parquet` | per-incident waveforms | time_s, t_rel_s, ax, ay, az | sensor_etl |
| `text_chunks.parquet` | parquet | `TextChunkRow` | text_etl |
| `video_index.parquet` | parquet | `VideoIndexRow` | video_etl |
| `incidents.parquet` | parquet (JSON-string list cols) | `IncidentRow` | assemble |
| `docs/_data/manifest.json` | JSON | ad-hoc dict + sha256s | tgfx.dataset |
| `docs/_data/alignment_ledger.jsonl` | JSONL | alignment record | tgfx.dataset |
| `data/splits/*.jsonl` | JSONL id manifests | {incident_id, failure_family, source_dataset} | tgfx.dataset |
| `docs/_eval/runs.jsonl` | JSONL | run record (git_sha, seed, metrics, gates) | eval.run |

## 6. API / interface map

- CLI: Typer app (6 commands), exit codes 0/1/2. (`src/cli.py`)
- Python API: `evaluate_build(cfg, tier, write)`, `build_dataset(...)`,
  `compute_metrics(outputs, gold)`, `load_fixture(name)`.
- UI: Streamlit single-page explorer. No HTTP API exists.
- **No model-serving, retrieval, or inference interfaces exist.**
