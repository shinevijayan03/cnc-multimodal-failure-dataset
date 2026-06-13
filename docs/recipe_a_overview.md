# Recipe A — Understanding & Overview

**Document status:** Phase 1 (design). Awaiting review.
**Audience:** senior ML-systems reviewer + the author (thesis context).
**Scope:** explain *what* Recipe A is, *why* it is shaped this way, and the
constraints/assumptions the implementation must respect. No code here.

---

## 1. The problem we are feeding

The dissertation builds models that produce **post-mortem failure explanations**
for CNC milling/router events. A good explanation is:

- **Temporally grounded** — it points at *when* in the signal/video the evidence
  occurs (e.g. "chatter onset at t≈ −4.2 s, peaking at t≈ +0.3 s").
- **Evidence-linked** — it explicitly cites *which* modality justifies each
  claim: a vibration span, a video span, and named SOP / maintenance passages.

To train and evaluate such models we need a dataset whose **atomic unit is an
incident window**: a short slice of time around a machining event, carrying all
three modalities plus labels. **Recipe A is the concrete strategy for building
that dataset.** Everything in this repo exists to turn raw, heterogeneous,
partly-licensed inputs into one tidy index — `incidents.parquet` — where each
row is a fully-linked multimodal incident.

### The mixing philosophy (why "Recipe A" and not "just download a dataset")

No public dataset contains synchronized vibration + video + maintenance text for
CNC failures. Recipe A therefore **mixes fidelity levels** deliberately:

| Modality | Fidelity | Why |
|----------|----------|-----|
| Sensors  | **Real** measured data | The temporal grounding must be physically honest; this is the backbone. |
| Video    | **Semi-synthetic alignment** | Real footage, but matched to sensor windows by *coarse label*, not by true simultaneous capture. |
| Text     | **Semi-synthetic** | Realistic SOP/maintenance manuals re-authored from public material; retrieved by topic relevance. |

The contract with downstream modeling is explicit: **sensor timing is ground
truth; video and text are *plausibly relevant* evidence, not co-recorded truth.**
This honesty is itself a dataset feature and is recorded per-row (e.g. an
`alignment_method` field, see open questions §8).

---

## 2. The three input modalities

### 2.1 Sensor backbone — REAL data

Primary, real CNC vibration / multi-channel data. Candidate sources:

- **Bosch CNC Machining Dataset** — long-horizon tri-axial accelerometer data
  from a brownfield CNC milling machine; benchmark, CC-BY-style licensing.
- **CNC Machining Data (Kaggle)** — additional real-world vibration data.
- **CNC Mill Tool Wear (Kaggle / SMART)** — lab dataset varying tool condition,
  feed, clamping (has explicit operating conditions → good label source).
- **Multi-Sensor CNC Tool Wear (Kaggle 2025)** — extra channels (cutting force);
  *optional*, enables multi-channel fusion.
- **Milling process life-cycle dataset (Nature Sci Data 2025)** — full tool life
  cycles under varied cutting conditions.

**Acquisition policy:** the pipeline **does not auto-download** these (Kaggle /
API auth, licensing). The author places raw files under
`data_raw/<dataset_name>/`. ETL reads them *once present* and skips datasets
whose folder is empty or `enabled: false`.

What sensor ETL must produce from these:

1. **Normalize** to a canonical schema: `time_s, ax, ay, az` (+ optional `ae,
   sound, force_*, spindle_current`).
2. **Estimate sampling rate** `fs_hz` per run (from timestamps, metadata, or fixed).
3. **Detect events** via configurable heuristics (default: sliding-window RMS
   threshold / z-score over a rolling baseline).
4. **Carve incident windows** around each event (default `[-60 s, +30 s]`).
5. **Persist** each window as Parquet/HDF5 with incident-relative time `t_rel_s`.
6. **Index** every window into `sensor_windows.parquet` (one row per window).

`sensor_windows.parquet` columns (minimum): `incident_id, source_dataset,
machine_family, failure_family, window_start_s, window_end_s, fs_hz, sensor_file`.

**Scale target:** ≥ **72 hours** of *selected incident windows* (not raw logging
time). With a 90 s window, that is ≈ **2,880 windows**. (Informational; verified
in evaluation, not enforced by ETL.)

### 2.2 Video corpus — ~1K clips, semi-synthetic alignment

Video shows the machining process and is matched to sensor windows by coarse
regime/condition, **not** by true co-recording.

- **Source 1:** author's own recordings of a CNC router/mill cutting material.
- **Source 2:** licensed / CC CNC machining footage (stock / YouTube), sliced
  into 5–10 s clips.

What video ETL must produce:

1. Read raw MP4s from `data_raw/video_raw/` (arbitrary substructure).
2. **Normalize** to a standard format (720p, 30 fps, H.264/MP4) via `ffmpeg`.
3. Build `video_index.parquet`: `video_id, video_file, video_fps, duration_s,
   regime_label, condition_label, source`.
4. Provide a **CSV-based tagging workflow** so the author labels each clip's
   `regime_label` (roughing/finishing/idle/plunge…) and `condition_label`
   (normal/tool_wear_visible/heavy_vibration/coolant_issue…).

**Scale target:** ≈ **1,000 clips**.

### 2.3 SOP + maintenance text — semi-synthetic manuals

Realistic but re-authored manuals (from public CNC maintenance blogs, training
slides, etc.; rewritten, not copied).

What text ETL must produce:

1. Read raw manuals (Markdown / DOCX / TXT) from `data_raw/text_manuals/`.
2. **Chunk** each doc to plain-text chunks of ~150–200 tokens, respecting
   paragraph / heading boundaries.
3. Build `text_chunks.parquet`: `doc_id, chunk_id, doc_type (sop|maintenance),
   text`.
4. **Tag** chunks (keyword/metadata) by topic — vibration, tool_wear, chatter,
   clamping, coolant, spindle, feed/speed — so retrieval can target them.

**Scale target:** equivalent of ≥ **300–400 pages** SOP + maintenance. Code must
scale beyond this; page count is not enforced programmatically.

---

## 3. How an incident window is defined

```
 amplitude
    ^
    |                         ┌── event (RMS/z-score crossing)
    |               .   .   . │ .   .
    |          . '             V        ' .
    |     . '      baseline                  ' . . .
    +----|--------------------|----------------|------------> time (s)
       window_start        t_event         window_end
         (event −60 s)                       (event +30 s)

         |<------------- incident window (90 s) ----------->|
                         saved with t_rel_s = time − t_event
```

- **Event** = a point/interval where a detection statistic (default: sliding RMS
  z-score of a chosen channel vs a rolling baseline) crosses a threshold.
- Events closer than `min_event_separation_s` are **merged** (one incident).
- Blips shorter than `min_event_duration_s` are **discarded**.
- The **incident window** is `[t_event − pre_event_s, t_event + post_event_s]`,
  default `[−60 s, +30 s]`. Windows running off the recording edge are dropped
  (`drop_partial_windows: true`).
- Stored with **incident-relative time** `t_rel_s` so every window shares a
  common coordinate frame (event at `t_rel_s ≈ 0`).
- **Sensor evidence spans** = the threshold-crossing interval(s), padded, capped
  at `max_spans`. These are the heuristic "this is where to look" intervals.

All of these are knobs in [`config/dataset.yaml`](../config/dataset.yaml) →
`sensor.event_detection` / `sensor.windowing` / `sensor.evidence_spans`.

---

## 4. How alignment between modalities works

The incident window from sensors is the **anchor**. The other modalities attach
to it:

```
                     ┌─────────────────────────────┐
                     │  SENSOR INCIDENT (anchor)    │
                     │  labels: failure_family,     │
                     │  regime, severity, phase     │
                     └───────────────┬─────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │ label_match                │ topic_match (keyword/BM25)  │
        v                            v                             v
 ┌─────────────┐            ┌─────────────────┐          ┌──────────────────┐
 │  VIDEO clip │            │  SOP chunks 1–3 │          │ Maintenance      │
 │ regime ==   │            │ topics derived  │          │ chunks 1–3       │
 │ incident    │            │ from failure_   │          │ topics derived   │
 │ regime      │            │ family          │          │ from failure_fam │
 └─────────────┘            └─────────────────┘          └──────────────────┘
```

- **Video ← incident:** choose a clip whose `regime_label` (and optionally
  `condition_label`) matches the incident's labels (`assemble.video_match`).
  Clips may be reused; idle clips are a fallback. **This match is heuristic and
  recorded as such.**
- **Text ← incident:** map `failure_family → topic tags`
  (`assemble.text_retrieval.failure_to_topics`), then retrieve 1–3 SOP chunks
  and 1–3 maintenance chunks whose tags/keywords match (BM25/keyword in v1,
  embeddings later).
- **Evidence spans:** sensor spans from threshold crossings; video spans
  heuristic at first (e.g. whole clip or a centered sub-span).

---

## 5. The unified output — `incidents.parquet`

One row per multimodal incident window. Minimum fields:

| Field | Meaning |
|-------|---------|
| `incident_id` | stable unique id |
| `source_dataset`, `machine_family`, `failure_family` | provenance + failure class |
| `window_start_s`, `window_end_s`, `fs_hz` | window bounds (original time) + sample rate |
| `sensor_file`, `sensor_channels` (JSON list) | path + channels present |
| `sensor_relevant_spans` (JSON list `{start_s,end_s}`) | heuristic evidence intervals |
| `video_file`, `video_fps`, `video_relevant_spans` | linked clip + spans |
| `sop_chunk_ids`, `maintenance_chunk_ids` (JSON lists) | retrieved text chunk ids |
| `phase_label`, `regime_label`, `severity_label`, `root_cause_label` | labels |
| `split` | `train` / `val` / `test` / `human_eval` |

This file is the **deliverable**; all four ETL stages exist to populate it.

---

## 6. Constraints (carry these into every design choice)

- **Sensors:** ≥ 72 h of selected incident windows; real data only; no
  auto-download; per-dataset reader + column map.
- **Video:** ≈ 1,000 normalized clips (720p/30fps/MP4); human-tagged regime &
  condition; alignment is label-heuristic.
- **Text:** ≥ 300–400 pages equivalent; ~150–200-token chunks; topic-tagged;
  retrieval-ready.
- **Honesty:** cross-modal links are heuristic and must be *labeled as such* per
  row, never presented as co-recorded.
- **Reproducibility:** seeded splits, config-driven, deterministic given the same
  raw inputs + config.
- **Idempotency:** re-running ETL on unchanged inputs reproduces the same outputs
  (stable ids, skip-if-exists).

---

## 7. Explicit assumptions

1. Raw data is **manually staged** by the author under `data_raw/<dataset>/`;
   the pipeline only reads what exists and skips the rest.
2. `ffmpeg` is installed and on `PATH`.
3. Failure-family labels are **partial** — many sensor windows are weakly/un-
   labeled. `failure_family` defaults to `unknown`; downstream tolerates this.
4. Video↔sensor and text↔sensor links are **relevance heuristics**, not physical
   synchronization.
5. Token counting for chunking can use `tiktoken`; a whitespace fallback is
   acceptable if a tokenizer is unavailable.
6. Parquet is the default tabular format (columnar, typed, pandas/pyarrow-native);
   HDF5 remains an option for raw waveform storage.
7. Sufficient local disk exists for normalized video + windowed sensor parquet.

---

## 8. Open questions (need author decisions)

> These are the decisions most likely to change downstream design. Flagged with
> a proposed default so implementation can proceed if unanswered.

1. **Storage format for sensor windows:** Parquet (default) vs HDF5? Parquet is
   simpler/portable; HDF5 better for very long raw waveforms.
   *Proposed: Parquet.*
2. **Event-detection heuristic:** RMS z-score (default) vs spectral/energy vs
   using datasets' own condition labels where present.
   *Proposed: RMS z-score, with `manual_labels` mode when a dataset ships labels.*
3. **Failure-family taxonomy:** confirm the closed set — e.g. `tool_wear,
   chatter, clamping_loss, coolant_fault, spindle_fault, unknown`. Drives text
   topic mapping and evaluation buckets.
4. **Severity definition:** derived from event amplitude/energy quantiles, or
   labeled manually? *Proposed: amplitude-quantile-derived, 3 bins
   (low/med/high).*
5. **Provenance/alignment flag:** add an `alignment_method` column to
   `incidents.parquet` documenting that video/text links are heuristic?
   *Proposed: yes.*
6. **Window length:** confirm `[−60 s, +30 s]`. Longer pre-roll captures slow
   tool-wear onset but costs hours-budget.
7. **Video true-overlap subset:** should a *small* set of author recordings be
   genuinely time-synced to a sensor capture (gold subset for `human_eval`)?
8. **Split policy:** group by `source_dataset` (default, prevents run leakage) vs
   group by physical run/tool id if available.

---

## 9. Glossary

- **Incident / incident window** — the 90 s multimodal sample; atomic dataset unit.
- **Event** — the detected machining anomaly anchoring an incident (`t_rel_s≈0`).
- **Regime** — coarse machining mode (roughing, finishing, plunge, idle…).
- **Condition** — coarse visual/health state (normal, tool_wear_visible…).
- **Evidence span** — `{start_s,end_s}` interval flagged as where the evidence is.
- **Chunk** — a ~150–200-token passage of SOP/maintenance text.
- **Semi-synthetic alignment** — real media linked by label relevance, not co-capture.
