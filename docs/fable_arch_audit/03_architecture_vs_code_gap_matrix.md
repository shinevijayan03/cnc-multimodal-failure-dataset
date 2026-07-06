# 03 — Architecture vs Code Gap Matrix

Statuses: IMPLEMENTED / PARTIAL / NOT IMPLEMENTED / STUB / BROKEN / UNKNOWN.
Confidence High unless noted. Build depth: Deep = real engineering required.

| Capability | Architecture Evidence | Code Evidence | File / Class-Function | Status | Gap | Build Depth |
|---|---|---|---|---|---|---|
| Interleaved sensor+video ingestion | D1 base layer | ETL 4 stages; label-matched linking | `src/etl/*` | IMPLEMENTED | sync constructed, not measured (I-8 caveat) | — |
| Incident window −12..0 s | D4 | ±8 s ETL spans + 12 s D10 sub-windows + [−12,0] query window | `src/tgfx/windows.py::resolve_query_window` | IMPLEMENTED (per approved D10) | — | — |
| Patch creation | D4 | (95, 3, 500) tokens, tails dropped | `src/features/patching.py` | IMPLEMENTED | — | — |
| PatchTST/TimesNet encoder | D1/D2/D4 | seeded GPU **autoencoder over patch-feature tokens**; PatchTST is a config slot only | `src/encoder/torch_ae.py`; `base.py::build_encoder` | PARTIAL | no real PatchTST/TimesNet architecture | Deep |
| Degradation-signature learning | D4 | self-supervised recon-error anomaly; AUROC 0.5798 vs real run-labels | `src/encoder/`; run record | PARTIAL | weak signal; gold labels absent | Deep (with F-02 labels) |
| sensor_summary / anomaly_score / important_interval | D4 | real per-window values + text summaries | `src/tgfx/sensor_features.py`; `src/retrieval/retriever.py::sensor_summary_text` | IMPLEMENTED | — | — |
| predicted_sensor_state | D4 | Not found in current codebase evidence | — | NOT IMPLEMENTED | classifier head missing | Medium |
| Frozen VLM video summary | D1/D2 | Qwen2.5-VL-3B bf16 frozen, greedy; tags fallback; 20/20 clips | `src/vision/summarizer.py` | IMPLEMENTED (3B per D15; LLaVA comparison absent) | LLaVA-NeXT-Video comparison | Deep (optional) |
| Video evidence intervals | prompt §3 | axis-spanning bar only; no within-incident visual timestamps | `src/ui/workbench.py::vlm_video_events` | PARTIAL | blocked by constructed sync (permanent for this corpus) | Deep + data |
| Timestamp normalization + logical incident time | D2 | incident-relative axis everywhere; alarm_state real | `src/tgfx/windows.py`; `src/temporal/grounding.py` | IMPLEMENTED | — | — |
| Aligned tuples (6-field) | D2 | exact shape, contract-valid, 3399 real | `contracts/core.py::AlignedTuple`; `src/temporal/grounding.py` | IMPLEMENTED | — | — |
| **SOP upload UI** | D3 | Not found in current codebase evidence (ingestion is filesystem-based) | `src/etl/text_etl.py` reads `data_raw/text_manuals` | NOT IMPLEMENTED | upload UI/API + security | Deep |
| Parsing / **OCR** / chunking | D3 | md/txt/docx/pdf text extraction + heading-aware chunking; **no OCR** | `text_etl.DocReader/Chunker` | PARTIAL | OCR hook for scanned PDFs | Medium |
| Semantic tagging (equipment/subsystem/step/alarm/mode) | D2/D3 | keyword **topic** tags only | `text_etl.TopicTagger` | PARTIAL | 5-facet metadata schema + tagger | Deep |
| BGE embeddings | D3 | BGE-base-en-v1.5, 768-d, GPU | `src/retrieval/embeddings.py` | IMPLEMENTED | — | — |
| Vector store | D1/D2/D3 | exact-cosine parquet store w/ embedder guard | `src/retrieval/store.py` | IMPLEMENTED | FAISS only if scale demands (D14) | — |
| Evidence/knowledge graph | D1/D2/D3 | typed nodes/edges; resolve-or-raise; 6063/17949 | `src/graph/evidence_graph.py` | IMPLEMENTED | richer KG relations (failure→symptom ontology) optional | — |
| Retriever (sensor+video query) | D1/D2/D3 | query from real sensor summary + failure family (+ optional clip summary); topic boost | `src/retrieval/retriever.py::IncidentRetriever` | IMPLEMENTED | video summary not yet auto-included in query at grounding time | Small |
| Sensor query tokens into frozen model | D2 | Not found in current codebase evidence | — | NOT IMPLEMENTED | Hvib→VLM prompt/token bridge | Deep |
| Evidence selection head | D1/D2 | deterministic top-k + boost rerank only | `retriever.retrieve` | PARTIAL | scoring/selection across all 3 modalities w/ confidence | Deep |
| Decoder LLM + structured output | D1/D2/D3 | contracts exist (`ExplanationOutput`, GBNF required by I-9); **no generator** | `contracts/explanation.py` only | NOT IMPLEMENTED | provider abstraction, prompt, JSON-schema→GBNF, guardrails | Deep |
| Faithfulness audit | D2 | fixture harness real; sensor verifier real; judge placeholder; AUROC/ECE placeholders | `src/eval/*` | PARTIAL | real-output adapter, unsupported-claim pipeline, report UI | Deep (I-6 process) |
| UI: synchronized timelines + evidence links | prompt §9 | shared clock, one-way video sync, grounded bars, tuples panel, export | `streamlit_app.py`, `src/ui/workbench.py` | PARTIAL | bidirectional video sync (platform-limited), clickable evidence→highlight, decoder + audit panels | Medium/Deep |
| Regression tests | prompt | 210 tests incl. E2E chain + AppTest UI | `tests/` | IMPLEMENTED (for built scope) | tests for future phases | ongoing |

Summary: 12 IMPLEMENTED · 7 PARTIAL · 4 NOT IMPLEMENTED · 0 BROKEN/UNKNOWN.
