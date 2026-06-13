# Implementation Plan — Recipe A Pipeline

**Status:** Phase 1 (design). Implementation gated on review approval.
**Companion docs:** [Recipe A Overview](recipe_a_overview.md) ·
[Architecture](architecture.md) · [Software Design](software_design.md).

This plan decomposes the build into stages. Each stage lists **inputs →
outputs**, **tools/libraries**, **estimated complexity**, **error modes &
mitigations**, and a **definition of done (DoD)**. Complexity is T-shirt sized
(S/M/L) with a rough effort note for planning, not a commitment.

---

## 0. Conventions used below

- **Idempotent**: re-running with unchanged inputs + config yields identical
  outputs (stable ids, skip-if-exists, atomic writes via temp-file + rename).
- **Config-driven**: every threshold/path/knob comes from
  [`config/dataset.yaml`](../config/dataset.yaml); no magic numbers in code.
- **Validated rows**: every index row is built through a typed data model
  (Pydantic) before being written; see [Software Design](software_design.md).

---

## Stage 0 — Project scaffolding & shared infrastructure

| | |
|---|---|
| **Inputs** | repo skeleton, `config/dataset.yaml` |
| **Outputs** | `src/common/` (config loader, logging, io utils, schemas), `pyproject.toml`/`requirements.txt`, CLI entrypoint stub, `tests/` scaffold |
| **Tools** | Python ≥3.10, `pydantic` v2, `pyyaml`, `pandas`, `pyarrow`, `numpy`, `loguru` (or stdlib logging), `typer` (CLI), `pytest` |
| **Complexity** | **S** (~0.5 day) |
| **Error modes** | missing config keys → fail fast with a precise message; bad YAML → surfaced at load; version drift → `config.version` check |
| **DoD** | `python -m src.cli --help` works; config loads + validates into a typed `PipelineConfig`; logging emits structured records; `pytest` collects 0 failures on an empty suite |

Build order rationale: every other stage imports `common/`. Do this first.

---

## Stage 1 — Sensor ETL  (`src/etl/sensor_etl.py`)

Turns raw vibration logs into windowed incidents + `sensor_windows.parquet`.

| | |
|---|---|
| **Inputs** | `data_raw/<dataset>/...` (CSV/H5/Parquet), `config.sensor.*` |
| **Outputs** | per-incident files in `data_processed/sensor_windows/<incident_id>.parquet` (cols incl. `t_rel_s`); index `sensor_windows.parquet` |
| **Tools** | `pandas`, `numpy`, `pyarrow`, `scipy.signal` (RMS/filter), `h5py` (Bosch) |
| **Complexity** | **L** (~2–3 days) — most numerically/heuristically involved stage |

**Sub-steps**

1. **Discover** runs: for each `enabled` dataset, glob its folder by `reader`.
2. **Read & normalize** to canonical schema via the dataset's `column_map`
   (rename, reorder, coerce dtypes, build/repair `time_s`).
3. **Estimate `fs_hz`** (`median_dt` default; `metadata`/`fixed` alternatives);
   optional resample to `resample_to_hz`.
4. **Detect events** (`rms_threshold` default): sliding RMS → rolling baseline →
   z-score → threshold crossings → merge/duration filters.
5. **Window** each event to `[−pre, +post]`; drop partial windows; add `t_rel_s`.
6. **Evidence spans** from threshold crossings (padded, capped).
7. **Persist** window parquet + append a validated `SensorWindowRow` to the index.

**Error modes & mitigations**

- *Unknown/garbled columns* → `column_map` required; unmapped file → log + skip
  (or fail if `fail_fast`).
- *Non-monotonic / missing timestamps* → reconstruct `time_s` from `fs_hz`; if
  neither timestamps nor known `fs_hz`, skip run with a clear warning.
- *Implausible `fs_hz`* (outside `min/max_plausible_hz`) → reject + log.
- *No events detected* in a run → emit zero windows (not an error); count it.
- *Window off recording edge* → drop (configurable).
- *Huge files* → process per-run, stream where possible; cap windows per run.

**DoD** — On a tiny synthetic CSV fixture with an injected burst, produces exactly
the expected number of windows, correct `t_rel_s` zero-crossing, and a valid
index row that round-trips through Parquet.

---

## Stage 2 — Text ETL  (`src/etl/text_etl.py`)

Independent of sensors; safe to build in parallel with Stage 1.

| | |
|---|---|
| **Inputs** | `data_raw/text_manuals/*.{md,txt,docx}`, `config.text.*` |
| **Outputs** | `text_chunks.parquet` (`doc_id, chunk_id, doc_type, text`, + `topic_tags`, `n_tokens`) |
| **Tools** | `markdown-it-py`/plain read, `python-docx` (DOCX), `tiktoken` (token count, whitespace fallback) |
| **Complexity** | **M** (~1 day) |

**Sub-steps**: read → to-plain-text (strip markup, keep headings) → split on
heading/paragraph boundaries → pack to ~`target_tokens` with overlap, respecting
`min/max_tokens` → assign `doc_type` (from path or front-matter) → keyword
topic-tag → validate `TextChunkRow` → write.

**Error modes** — unreadable/binary DOCX → skip + log; empty doc → 0 chunks;
oversized heading-less paragraph → hard-split at `max_tokens`; tokenizer
unavailable → whitespace estimate (logged once).

**DoD** — A fixture manual yields chunks all within `[min,max]` tokens, no chunk
crosses a heading, and at least the expected topic tags are assigned.

---

## Stage 3 — Video ETL  (`src/etl/video_etl.py`)

Also independent of sensors.

| | |
|---|---|
| **Inputs** | `data_raw/video_raw/**.mp4`, optional `video_tags.csv`, `config.video.*` |
| **Outputs** | normalized clips in `data_processed/video/`; `video_index.parquet` |
| **Tools** | `ffmpeg`/`ffprobe` via `subprocess`, `pandas` |
| **Complexity** | **M** (~1–1.5 days, mostly ffmpeg edge cases) |

**Sub-steps**: discover MP4s → `ffprobe` for fps/duration → normalize (720p/30fps
/H.264) unless already conformant → derive `video_id` → merge human
`video_tags.csv` (regime/condition/source) → validate `VideoIndexRow` → write.

**Error modes** — `ffmpeg` missing → fail Stage 3 only, with install hint;
corrupt MP4 → skip + log; clip outside `[clip_min_s, clip_max_s]` → flag (don't
auto-cut in v1); missing tags → labels = `unknown`, counted for the eval report.

**DoD** — A short fixture MP4 normalizes to 720p/30fps and appears in the index
with correct probed duration and merged tags.

---

## Stage 4 — Incident Assembly  (`src/etl/assemble_incidents.py`)

Joins the three indices into `incidents.parquet`. Depends on Stages 1–3.

| | |
|---|---|
| **Inputs** | `sensor_windows.parquet`, `video_index.parquet`, `text_chunks.parquet`, `config.assemble.*` |
| **Outputs** | `incidents.parquet` (full schema in [Overview §5](recipe_a_overview.md)) |
| **Tools** | `pandas`, `rank-bm25` or sklearn TF-IDF (keyword retrieval), `numpy` (split) |
| **Complexity** | **M–L** (~1.5–2 days) |

**Sub-steps** per sensor incident:
1. Derive/default labels (`regime/phase/severity/root_cause`).
2. **Video match** (`label_match`): filter clips by regime (± condition), pick
   (seeded) one; fallback to idle; record `alignment_method`.
3. **Text retrieval**: `failure_family → topics`; BM25/keyword over each
   `doc_type`; take `[min,max]` chunks each → `sop_chunk_ids`,
   `maintenance_chunk_ids`.
4. Carry sensor spans; set heuristic `video_relevant_spans`.
5. Assign `split` (grouped by `source_dataset`, seeded fractions).
6. Validate `IncidentRow`; collect.
Finally write `incidents.parquet` atomically.

**Error modes** — no matching video → idle fallback or null + flag; no matching
chunks → relax topics, else fewer than min + flag; empty upstream index → fail
fast with which stage to run; split rounding → deterministic remainder assignment.

**DoD** — From tiny fixtures of all three modalities, produces ≥1 fully-linked
incident with valid JSON list fields, a split label, and no dangling ids.

---

## Stage 5 — CLI, orchestration & logging  (`src/cli.py`)

| | |
|---|---|
| **Inputs** | all stages, `config/dataset.yaml` |
| **Outputs** | subcommands: `sensor`, `text`, `video`, `assemble`, `all`; `--config`, `--dry-run`, `--limit` |
| **Tools** | `typer`, structured logging |
| **Complexity** | **S–M** (~0.5–1 day) |
| **Error modes** | partial pipeline (missing upstream output) → actionable error naming the command to run first |
| **DoD** | `python -m src.cli all --config config/dataset.yaml --dry-run` validates inputs end-to-end without writing |

---

## Stage 6 — Tests & fixtures  (`tests/`)

Built incrementally *with* each stage (not after). See
[Test Strategy & Plan](test_strategy_and_plan.md) and [Test Cases](test_cases.md).

| | |
|---|---|
| **Outputs** | `tests/unit/`, `tests/integration/`, synthetic fixtures (tiny CSV w/ injected burst, 2-page manual, 2 s MP4) |
| **Tools** | `pytest`, `pytest-cov`, `numpy` (signal synthesis), tiny generated MP4 |
| **Complexity** | **M** (ongoing) |
| **DoD** | unit coverage on numeric core (fs est., RMS, windowing, chunking, split); one end-to-end integration test green |

---

## Stage 7 — Evaluation & reporting  (`notebooks/` + `src/evaluate.py`)

| | |
|---|---|
| **Inputs** | `incidents.parquet` + the three indices |
| **Outputs** | metrics report (incident hours, family/regime distribution, % with SOP+maint chunk, missing-file/malformed-JSON rates) per [Evaluation Criteria](evaluation_criteria.md) |
| **Tools** | `pandas`, `matplotlib`, notebook |
| **Complexity** | **S–M** |
| **DoD** | one command/notebook prints the metric table and pass/fail vs thresholds |

---

## Build order & dependency graph

```
Stage 0 (common) ──► Stage 1 (sensor) ─┐
                ├──► Stage 2 (text)    ─┼──► Stage 4 (assemble) ──► Stage 7 (eval)
                └──► Stage 3 (video)   ─┘
                          Stage 5 (CLI) wraps all · Stage 6 (tests) spans all
```

Stages 1–3 are mutually independent and may be built/tested in parallel after
Stage 0. Stage 4 is the only true join point.

---

## Milestones

### M1 — Minimal Viable End-to-End (MVP / "demo build")
*Goal: prove the whole chain on a tiny demo subset.*
- Stage 0 + one `generic_csv` sensor reader + RMS detection + windowing.
- Text ETL on a handful of manuals; whitespace tokenizer acceptable.
- Video ETL on 2–3 clips with hand-written tags (ffmpeg normalize).
- Assembly producing a few fully-linked incidents + a split.
- One green integration test; eval notebook runs.
- **Exit criteria:** `incidents.parquet` exists with ≥1 valid multimodal row
  from demo inputs; no dangling references; JSON fields parse.

### M2 — Extended / thesis-scale build
- All enabled sensor readers (incl. Bosch H5); resampling; `manual_labels` mode.
- `tiktoken` chunking; embedding-based text retrieval option.
- Full video corpus normalization (~1K clips).
- BM25 retrieval; severity bucketing; `alignment_method` provenance.
- Hits scale targets (≥72 h windows, ~1K clips, ≥300–400 pp text) — verified by
  the evaluation report, iterated until thresholds pass.

---

## Top risks (tracked from day 1)

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Raw formats differ from assumptions (cols, units, fs) | Sensor ETL rework | per-dataset `reader` + `column_map`; validate on one real sample early |
| Event heuristic over/under-detects | Wrong incident set / hours-budget miss | tunable thresholds; eval report on event density; `manual_labels` mode |
| `ffmpeg` env issues on Windows | Video stage blocked | detect + clear install hint; isolate to Stage 3 |
| Weak/missing failure labels | Sparse text matching | `unknown` defaults + topic fallback; track % linked in eval |
| Cross-modal links mistaken for ground truth | Scientific validity | `alignment_method` flag + honesty documented in Overview |
| Disk blow-up (video + windows) | Build halts | normalize to 720p; cap windows/run; gitignored data dirs |
