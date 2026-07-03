# 13 — Recommended Build Roadmap

The user-supplied 13-phase template is kept, **re-scoped to what the audit
found**: Phases 1–3 are mostly verification/extension of existing code (the
codebase is already stable and runnable), Phases 4–13 are genuine deep builds.
Every phase ends with: app run → validation report → rubric → user review gate.
Constitution rules bind throughout (frozen VLM I-1, one feature path I-3,
test quarantine I-4, seeds/run records I-5, metric freeze I-6, GBNF I-9,
ratchet I-10, ≤600-line branches I-11).

| Phase | Title | Audit-adjusted scope | Effort | Depends on |
|---|---|---|---|---|
| 1 | Runnable baseline | **Mostly done already** (RUNS). Remaining: fresh-clone bootstrap (tiny bundled sample data or generator), re-measure coverage, `.env.example` placeholder, runbook doc | Small | — |
| 2 | Sensor ingestion + incident windowing | **Largely exists.** Remaining: resolve window convention (decision log — R-4), add alarm-anchored -12..0s query window + 12s contract sub-window carving, sensor evidence IDs matching `SW_*` scheme | Small–Medium | 1 |
| 3 | Patch creation + feature extraction | Add `spectral_bands()` (4 bands) to the one feature path; refactor ETL RMS to import it (fix I-3 duplication); patcher (window → tokens); heuristic anomaly score + important-interval extraction wired to contract `SensorWindow` | Medium | 2 |
| 4 | Pluggable sensor encoder | Encoder abstraction + deterministic lightweight baseline (linear/1D-CNN) producing Hvib; optional PatchTST behind config; introduces torch; train/infer separation, seeded | Large | 3 |
| 5 | SOP embeddings + vector store | Embedding interface (BGE per contract; local), vector DB (recommend local FAISS/Chroma/SQLite — decision log), richer metadata tags, SOPChunk producer + citation format | Medium | 1 |
| 6 | Evidence graph + retriever | Node/edge schema over sensor/video/SOP/failure/mode; graph store; runtime `retrieve(sensor+video context)`; ranking; evidence-ID resolution service (backs I-2) | Large | 5 |
| 7 | Video ingestion + VLM summaries | Incident-time clip extraction; frozen Qwen2.5-VL adapter with transparent stub mode; `VideoClip` producer with sync_provenance + confidence | Large (R/P) | 2 |
| 8 | Temporal grounding layer | `src/temporal/`: normalize all modalities to incident-relative time; produce validated `AlignedTuple`s; chronology consistency checks; ledger cross-check | Medium–Large | 3, 6, 7 |
| 9 | Multimodal fusion | Projection to joint space; deterministic cross-modal correlation baseline (trainable cross-attention deferred until v1 gates green — I-1 spirit) | Large | 4, 6, 7, 8 |
| 10 | Evidence selection head | Scoring + top-K per modality + confidence; traceable bundle | Medium | 9 |
| 11 | Constrained decoder | Provider abstraction (mock + local GBNF path); prompt template; JSON-Schema→GBNF compiler; B1 free-text baseline; every claim evidence-linked | Large (R/P) | 10 |
| 12 | Eval + faithfulness audit integration | Feed real outputs to `compute_metrics`; real AUROC/ECE; quarantine guard (R-8); judge study scaffold; audit report writer; gates G3/G7–G11. **I-6 process:** decision-log + meta-test rerun + re-score | Medium–Large | 11 |
| 13 | End-to-end demo + hardening | One-command incident→explanation→audit; Streamlit "Explain" page; regression tests; docs | Medium | 12 |

## Cross-cutting workstream (not a phase)

**Gold mini-set curation** (R-1): 20–40 val incidents with human sub-cause
labels + true evidence spans, curated during Phases 3–6, required before any
learned component's numbers are quoted. Test split remains quarantined (I-4).

## Sequencing rationale

1. Phases 2–3 are cheap and unblock everything sensor-side; they also retire
   the two highest-probability rework risks (R-4 window convention, R-5 I-3 drift).
2. Text/RAG track (5–6) is independent of the encoder track (3–4) — can be
   parallelized if desired, but serial keeps diffs small (I-11).
3. Video/VLM (7) is the highest-uncertainty phase; scheduling it after the
   retriever means a stub video path never blocks grounding (8).
4. Fusion→selection→decoder→eval (9–12) is strictly dependency-ordered.
5. Every phase must append a run record when it produces a metric (I-5/I-7),
   and merges require green contracts + no val KPI regression (I-10).

## First build phase recommendation

**Start with Phase 1 (thin) + the R-4 window-convention decision.**
Phase 1 is small because the audit classified runtime as RUNS; its real
deliverables are the fresh-clone bootstrap and re-measured coverage. The
window-convention decision (user input required) gates Phase 2/3 design and
should be made at the Phase 1 review gate.
