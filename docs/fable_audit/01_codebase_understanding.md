# 01 — Codebase Understanding

## What the codebase is trying to achieve

A **temporally grounded, evidence-linked CNC failure-explanation system**
(dissertation project "TGFX"): vibration time-series + machine video + SOP/
maintenance documentation → per-incident evidence, aligned on an incident-
relative time axis, with every claim carrying resolvable evidence IDs.
Governed by a 12-rule constitution (`CLAUDE.md` I-1…I-12) and a decision log
(`docs/_sdd/decisions.md` D1–D15). Build Phases 1–7 of a 13-phase roadmap
(`docs/build_plan/01_phase_roadmap.md`) are implemented; fusion (9–10),
decoder LLM (11), full eval integration (12), and e2e demo (13) remain.

## System inventory (all verified by reading the files this session)

| Area | Evidence |
|---|---|
| Main entry points | `src/cli.py` (Typer: sensor/text/video/assemble/all/evaluate); module `main()`s in `src/tgfx/windows.py`, `src/tgfx/sensor_features.py`, `src/encoder/train.py`, `src/retrieval/build_index.py`, `src/retrieval/search.py`, `src/graph/evidence_graph.py`, `src/temporal/grounding.py`, `src/vision/build_summaries.py`; `streamlit_app.py` |
| App framework | Streamlit 1.54 single-page workbench (`streamlit_app.py`, ~600 lines; `st.fragment(run_every=0.5s)` shared playback clock) |
| ETL / data processing | `src/etl/sensor_etl.py` (readers, Normalizer, FsEstimator, EventDetector, WindowCarver, EvidenceSpanExtractor), `text_etl.py` (DocReader/Chunker/TopicTagger), `video_etl.py` (ffprobe/ffmpeg + TagMerger), `assemble_incidents.py` (LabelDeriver/VideoMatcher/TextRetriever/SplitAssigner) |
| Feature path (constitution I-3) | `src/features/vibration.py` — rms, variance, kurtosis, feature_delta, rose, sliding_rms, spectral_bands (4), band_edges_hz; `src/features/patching.py` (D12 patch tokens) |
| Model/AI modules | `src/encoder/` (baseline projection + GPU autoencoder → Hvib + anomaly, seeded trainer with run records); `src/retrieval/` (BGE embedder + hashing fallback, VectorStore, IncidentRetriever); `src/vision/` (frozen Qwen2.5-VL-3B summarizer + tags-only fallback, frame sampler, builder); `src/graph/` (NetworkX evidence graph = I-2 resolution service); `src/temporal/grounding.py` (AlignedTuple producer) |
| Contracts | `contracts/core.py` (SensorWindow, VideoClip, SOPChunk, TimelineEntry, IncidentTuple, AlignedTuple), `contracts/explanation.py` (ChainClaim, ExplanationOutput) — pydantic v2 with span/chronology validators |
| Eval layer (code-frozen, I-6) | `src/eval/` — metrics (IoU, attribution, unsupported-claim rate…), fixtures, verify_sensor (rule-based), verify_llm (placeholder), run.py (run records → `docs/_eval/runs.jsonl`); `src/evaluate.py` (dataset-quality PASS/WARN/FAIL) |
| UI components | `src/ui/incident_explorer.py` (data helpers), `src/ui/workbench.py` (~600 lines pure logic: PlaybackState, TimelineEvent builders, real-artifact surfacing, export) |
| Storage | Parquet artifacts under `data_pipeline/data_processed*`: sensor_windows, text_chunks, video_index, incidents, subwindows, sensor_features, encoder_tokens, hvib, vector_store, video_summaries, aligned_tuples + `evidence_graph.json`; `docs/_data/` (manifest, ledger, quality_labels); `data/splits/*.jsonl` (test quarantined, I-4) |
| Config layer | `src/common/config.py` — typed pydantic `PipelineConfig` (paths/sensor/video/text/assemble/encoder/retrieval/vision/runtime), single-YAML loader with version check |
| Test layer | 210 tests: `tests/{unit,integration,contracts,eval_meta,ui}` incl. E2E chain test and in-process Streamlit AppTest render tests |
| Scripts | `scripts/build_dataset.py`, `generate_sample_data.py`, `derive_quality_labels.py` |
| External integrations | HF models (BGE-base-en-v1.5, Qwen2.5-VL-3B-Instruct) downloaded at first use; ffmpeg on PATH; **no network APIs, no secrets** |

## Data flow (runtime order, all stages executed this session)

```text
raw CSV/PDF/MP4 → ETL (4 stages) → incidents.parquet (1702)
  → D10 sub-windows (3399, SW_* ids)          [src/tgfx/windows.py]
  → features + anomaly + important intervals   [src/tgfx/sensor_features.py]
  → encoder tokens → Hvib + encoder anomaly    [src/encoder/, GPU, seeded]
  → BGE vector index (934 chunks)              [src/retrieval/build_index.py]
  → evidence graph (6063 nodes/17949 edges)    [src/graph/]
  → VLM clip summaries (20/20, frozen 3B)      [src/vision/]
  → aligned tuples (3399; retriever + summaries + graph resolution)
                                               [src/temporal/grounding.py]
  → Streamlit workbench renders all of the above
```

## Not found in current codebase evidence

`src/fusion/` (joint feature space, evidence selection head), `src/explain/`
(decoder LLM, GBNF grammar), `scripts/eval_test.py`, real KPI gates G3/G7–G11,
HTTP API layer, user-note persistence. These match the roadmap's unbuilt
Phases 9–13 — documented gaps, not defects.
