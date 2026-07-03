# 02 — Current Codebase Understanding

## Main purpose

The repository is a **dataset-engineering pipeline** ("Recipe A") that builds a
multimodal CNC failure-explanation *dataset*, plus the beginnings of the TGFX
(Temporally Grounded Failure eXplanation) *evaluation substrate*. It is **not
yet a model system**: there is no encoder, no VLM, no retriever service, no
fusion, and no explanation generator.

Evidence: `README.md` lines 1–25 ("Data-engineering pipeline that builds a
multimodal CNC failure-explanation dataset"); `docs/_sdd/tasks.md` (T-10..T-22
"Not started").

## What each subsystem actually does

### 1. Sensor ETL — `src/etl/sensor_etl.py`

- Readers: `read_generic_csv` (recursive CSV discovery; parent folder `good/bad`
  surfaced as quality metadata), `read_bosch_h5` (lazy h5py import).
- `Normalizer`: column-map renaming to canonical `ax/ay/az`, synthetic `time_s`
  from fixed `fs_hz` (staged corpus has no time column — `config/dataset.yaml`
  `sensor.datasets[kaggle_cnc].fs_hz: 2000`).
- `FsEstimator`: median-dt / metadata / fixed, plausibility-bounded.
- `EventDetector`: sliding-window RMS (window 1.0s, hop 0.25s) with
  `quantile | zscore | absolute` thresholding; event merging and min-duration
  filters. Config currently uses `quantile 0.80` because the staged corpus is
  continuous machining (config comment, lines 112–118).
- `WindowCarver`: carves `pre_event_s=8.0` / `post_event_s=8.0` windows with
  incident-relative `t_rel_s`.
- `EvidenceSpanExtractor`: threshold-crossing spans, padded, max 5.
- Output: per-incident waveform parquet + `sensor_windows.parquet` index rows
  validated by `SensorWindowRow` (`src/common/schemas.py:92`).

### 2. Text ETL — `src/etl/text_etl.py`

- `DocReader`: md/txt/docx/pdf with page caps; doc-type inference (sop vs maintenance).
- `Chunker`: token-target chunking (target 175, min 80, max 220, overlap 20),
  heading-aware; tokenizer is tiktoken cl100k with whitespace fallback.
- `TopicTagger`: keyword → topic tags from `config/dataset.yaml text.topic_keywords`.
- Output: `text_chunks.parquet` (`TextChunkRow`). **No embeddings are computed.**

### 3. Video ETL — `src/etl/video_etl.py`

- `FfprobeReader`/`FfmpegNormalizer`: probe + normalize to 720p/30fps/h264 mp4,
  5–10s clips; skips cleanly when ffmpeg is absent.
- `TagMerger`: joins `video_tags.csv` regime/condition labels.
- Output: `video_index.parquet` (`VideoIndexRow`). **No content understanding** —
  no frames are analyzed, no VLM is called.

### 4. Incident assembly — `src/etl/assemble_incidents.py`

- `LabelDeriver`: **weak deterministic label scaffolding** — failure family /
  severity derived from amplitude buckets and hashed incident keys, not curated
  ground truth (README "Demo-build note"; `manifest.json` `label_status:
  weak_signal_derived_not_ground_truth`).
- `VideoMatcher`: label-match (regime) with idle fallback; clip reuse allowed.
- `TextRetriever`: retrieves SOP/maintenance chunks by `failure_to_topics`
  keyword-topic mapping (config `assemble.text_retrieval.method: keyword_bm25`).
- `SplitAssigner`: grouped split, fractions 0.7/0.15/0.10/0.05.
- Output: `incidents.parquet` (`IncidentRow`) — the cross-modal join table.

### 5. Dataset-quality evaluation — `src/evaluate.py`

Pure functions over the parquet indices; MVP/extended tier thresholds; hard
integrity gates (missing files, dangling chunk ids, bad spans, duplicates);
grade PASS/WARN/FAIL. Current staged build: **PASS** (mvp tier, run 2026-07-03).

### 6. TGFX contracts — `contracts/`

- `core.py`: `SensorWindow` (12s sub-window inside [-60,+30], exactly ax/ay/az,
  4 spectral-energy bands), `VideoClip` (**sync_provenance: measured|constructed**
  — constitution I-8), `SOPChunk` (declares embedding model BAAI/bge-base-en-v1.5,
  dim 768 — *declaration only, no embedding code exists*), `TimelineEntry`,
  `IncidentTuple`, `AlignedTuple` (evidence_ids min_length=1 — I-2).
- `explanation.py`: `ChainClaim` (span inside [-60,+30], evidence_ids >= 1),
  `ExplanationOutput` (root_cause_ranked 1–5 of the 5-class `SubCause` taxonomy,
  chronologically-ordered chain enforced by validator, confidence in [0,1]).

### 7. TGFX eval harness — `src/eval/`

- `metrics.py`: interval IoU, schema_valid_rate, attribution precision/recall,
  unsupported_claim_rate, wrong_time_claim_rate, evidence recall@5, detection
  P/R/F1 (+ degenerate AUROC placeholder), root-cause top-1/top-3, ECE proxy.
- `fixtures.py`: hand-authored oracle / corrupted_intervals / mixed fixtures.
- `verify_sensor.py`: rule-based claim verifier using `src.features.vibration.rose`
  (single feature path — I-3).
- `verify_llm.py`: **placeholder** deterministic judge (fixture-only).
- `run.py`: run records with `git_sha`, `config_hash`, `seed` (default 20260702),
  `dataset_manifest_hash` appended to `docs/_eval/runs.jsonl` (I-5, I-7).

### 8. Feature path — `src/features/vibration.py`

`rms`, `variance`, `kurtosis`, `feature_delta`, `rose`. This is the constitution
I-3 "one feature path". **Gap:** no spectral-band function here yet, although
`SensorWindow.spectral_energy` requires 4 bands and the sensor ETL computes RMS
independently in `EventDetector._sliding_rms` (numpy path) — a latent I-3
tension to resolve when the encoder work starts.

### 9. TGFX dataset substrate — `src/tgfx/dataset.py`, `scripts/build_dataset.py`

Builds `docs/_data/manifest.json` (artifact hashes, counts, label status),
`docs/_data/alignment_ledger.jsonl` (per-incident alignment provenance with
`sync_provenance: constructed`), and `data/splits/*.jsonl` ID manifests.

### 10. UI — `src/ui/incident_explorer.py`, `streamlit_app.py`

Streamlit incident explorer over the processed parquet tables: incident picker,
vibration window plot, linked video, retrieved chunks, alignment summary.
Verified to start headless with healthz 200.

## Configuration

Single YAML (`config/dataset.yaml`) parsed into typed pydantic config models
(`src/common/config.py`). Global seed 1337 for the *pipeline*; TGFX eval uses
seed 20260702 (I-5 default) — two seed regimes, documented.

## Test strategy (current)

107 tests: unit (per ETL component, synthetic signals), integration
(pipeline-level), contracts (pydantic), eval_meta (metric meta-tests including
corrupted-fixture degradation), ui (helper-level + opt-in browser smoke).
Result on audit day: 106 passed, 1 skipped (browser smoke, opt-in).

## Current limitations (verified)

1. Labels are weak scaffolding, not curated gold (README; manifest.json).
2. `regime_dist: {'unknown': 1702}` — regimes never derived for incidents (evaluate output).
3. Video-incident alignment is `constructed`, not measured (ledger; I-8 caveat).
4. No ML anywhere: no encoder, embeddings, vector DB, graph, fusion, decoder.
5. TGFX metrics run only against hand-authored fixtures, not real model outputs.
6. `verify_llm.py` judge is an explicit placeholder.
