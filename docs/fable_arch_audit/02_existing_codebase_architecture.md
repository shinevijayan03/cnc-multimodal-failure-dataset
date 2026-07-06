# 02 — Existing Codebase Architecture (verified this session)

Pipeline (all stages executed on the real corpus, 2026-07-03):

```text
raw CSV/PDF/MP4
 → ETL: src/etl/{sensor,text,video}_etl.py + assemble_incidents.py
   → incidents.parquet (1702) · text_chunks.parquet (934) · video_index (20)
 → D10 sub-windows: src/tgfx/windows.py → subwindows.parquet (3399 SW_* ids)
 → features: src/tgfx/sensor_features.py (one path src/features/vibration.py,
   patches src/features/patching.py) → sensor_features.parquet
 → encoder: src/encoder/ (seeded GPU AE) → hvib.parquet + run record
 → retrieval: src/retrieval/ (BGE-768 GPU + hashing fallback, cosine store,
   IncidentRetriever w/ topic boost) → vector_store.parquet
 → graph: src/graph/evidence_graph.py (networkx+JSON, resolve-or-raise = I-2)
   → evidence_graph.json (6063 nodes / 17949 edges)
 → vision: src/vision/ (FROZEN Qwen2.5-VL-3B bf16, greedy; tags fallback)
   → video_summaries.parquet (20/20 vlm, mean conf 0.95)
 → grounding: src/temporal/grounding.py → aligned_tuples.parquet
   (3399 tuples, resolution 1.0, 0 chronology violations, run record w/ G2)
 → UI: streamlit_app.py + src/ui/workbench.py (shared playback clock,
   synchronized cursors, live retrieval, grounded bars, export)
```

## Current Runtime Map

| App Area | Entry File | Runtime Command | Current Status | Evidence |
|---|---|---|---|---|
| Dataset ETL + gate | `src/cli.py` | `python -m src.cli all` / `evaluate --tier mvp` | RUNS; GRADE: PASS | this session |
| Sub-windows/features | `src/tgfx/*` | module CLIs | RUNS (3399 windows) | build outputs |
| Encoder | `src/encoder/train.py` | `--seed 20260702` | RUNS on cuda; deterministic; AUROC 0.5798 vs 0.4170 heuristic | run record |
| Retrieval | `src/retrieval/*` | build_index / search | RUNS (934 chunks, 6.24 s GPU) | build output |
| Graph | `src/graph/evidence_graph.py` | build / `--resolve <id>` | RUNS | build output |
| VLM | `src/vision/build_summaries.py` | module CLI | RUNS (~20 s/clip after max_pixels fix) | run log |
| Grounding | `src/temporal/grounding.py` | module CLI | RUNS (G2 = 1.0) | run record |
| UI | `streamlit_app.py` | `streamlit run …` | RUNS — http://localhost:8501 healthz 200 | probe |
| Tests | `tests/` | `pytest -q` | 209 passed, 1 skipped | this session |

Contracts (`contracts/`): SensorWindow, VideoClip, SOPChunk, TimelineEntry,
IncidentTuple, AlignedTuple, ChainClaim, ExplanationOutput — producers exist
for all except ChainClaim/ExplanationOutput (decoder pending). Eval substrate
(`src/eval/`, code-frozen I-6): fixture metric harness, rule-based sensor
verifier, placeholder LLM judge, run records. Full detail:
`docs/fable_audit/01_codebase_understanding.md`.
