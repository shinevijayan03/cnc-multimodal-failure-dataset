# 08 — How the RAG Is Implemented & How the SOP-RAG Diagram Is Realized

**Date:** 2026-07-07 · **Tree:** branch `codex/complete-pending-phases` @ `f20282a`, clean
**Diagram audited:** the SOP-RAG architecture (diagram **D3** in `01_architecture_ingestion.md`):
*UI for uploading SOP documents → Document Processor (parsing, OCR, chunking, tagging) →
Embedding Generation: BGE → {Vector Store, Evidence Graph} → Retriever (queried by a vibration
sensor summary "RMS rise.." and a video summary "Wobble..") → Decoder LLM: Gemma → Output.*

**Method:** every claim below was verified by reading the referenced source file in full and by
checking that the named artifact exists under `data_pipeline/data_processed/` on this date. No
number is quoted from memory; run-level numbers cite `docs/_eval/runs.jsonl` (20 records) or the
decision log.

---

## 1. Verdict in one paragraph

Seven of the diagram's eight boxes are realized as working, tested code with real artifacts on
disk; the RAG path is a true **embedding-based retrieval** system (BGE-base-en-v1.5 on the local
GPU → brute-force cosine vector store → topic-boosted re-ranking), not the keyword matching that
the original Recipe A assembler used. The two divergences from the picture are deliberate and
logged: **(a)** there is no SOP *upload UI* — ingestion is a filesystem drop + CLI stage
(capability #11 in `01_architecture_ingestion.md` remains open, and "OCR" is only text
extraction, §6.1); **(b)** the decoder is **Qwen2.5-7B-Instruct**, not Gemma, per decision **D2**
(Gemma-2-9B remains the named ablation). Everything between those endpoints — chunking, tagging,
BGE embeddings, vector store, evidence graph, retriever with sensor+video queries, GBNF-constrained
decoder, evidence-linked output — exists and is wired end-to-end.

---

## 2. Diagram-node → code map

| Diagram node | Realized by | Key artifact | Run command |
|---|---|---|---|
| UI for uploading SOP document | **Not realized as UI.** Manual drop into `data_pipeline/data_raw/text_manuals/` + CLI stage | raw md/txt/docx/pdf files | `python -m src.cli text` |
| Document Processor (parsing, OCR, chunking, tagging) | `src/etl/text_etl.py` — `DocReader` (md/txt/docx/pdf), `Chunker` (heading-aware, ~175-token windows, 20-token overlap), `TopicTagger` (keyword→topic map from config) | `text_chunks.parquet` (934 chunks) | `python -m src.cli text` |
| Embedding Generation: BGE | `src/retrieval/embeddings.py` — `BgeEmbedder` (`BAAI/bge-base-en-v1.5`, 768-d, L2-normalized, sentence-transformers on CUDA per D11/D14; BGE query prefix at `embeddings.py:23`) | — | (invoked by build_index) |
| Vector Store | `src/retrieval/store.py` — `VectorStore`: exact brute-force cosine, metadata filters, single-parquet persistence that records its embedder name and refuses mismatched query embedders (`store.py:94-99`) | `vector_store.parquet` (934 × 768; built on the RTX 3060 in 6.24 s per D14) | `python -m src.retrieval.build_index` |
| Evidence Graph | `src/graph/evidence_graph.py` — NetworkX DiGraph (D7): node kinds `incident/window/chunk/doc/video/failure_family`, edges `has_window/linked_sop/linked_maintenance/part_of/video_matched(sync_provenance)/classified_as`; `resolve()` is the I-2 evidence-ID resolution service | `evidence_graph.json` | `python -m src.graph.evidence_graph` |
| Retriever (red box) | `src/retrieval/retriever.py` — `IncidentRetriever`: builds the query from failure family + **real sensor summary** + optional **VLM clip summary**, over-fetches 3k, re-ranks with a +0.05-per-matching-topic boost (`retriever.py:16,66-89`) | consumed downstream | `python -m src.retrieval.search --query "..."` (ad-hoc) |
| Vibration sensor data summary ("RMS rise..") | `retriever.sensor_summary_text()` (`retriever.py:19-33`) and per-window `temporal/grounding.window_sensor_summary()` — deterministic templating over the single feature path (I-3, D12): RMS trend, peak interval, kurtosis, anomaly scores | `sensor_features.parquet`, `subwindows.parquet` | `python -m src.tgfx.sensor_features` |
| Video data summary ("Wobble..") | `src/vision/summarizer.py` — frozen **Qwen2.5-VL-3B-Instruct** bf16 on GPU (I-1: eval mode, `no_grad`, greedy; 3B not 7B per D11 VRAM analysis), strict-JSON prompt → `{summary, labels, confidence}`; transparent `tags_only` fallback | `video_summaries.parquet` | `python -m src.vision.build_summaries` |
| Decoder LLM | `src/explain/providers.py` — `LlamaCppProvider`: **Qwen2.5-7B-Instruct Q4_K_M** GGUF via llama.cpp (D2; `models/gguf/…` present on disk), temperature 0, seed 20260702, **GBNF grammar** compiled from the `ExplanationOutput` JSON Schema (I-9, `src/explain/grammar.py`); plus deterministic `MockProvider` baseline | `explanations.parquet` | `python -m src.explain.generate --provider llama` |
| Output | `contracts.ExplanationOutput` → report dict (failure_hypothesis, chronology, evidence per modality, sop_links, corrective_actions, confidence, uncertainties, unsupported_claims) rendered in the workbench "AI Explanation" tab (`streamlit_app.py:592-616`) | `explanations.parquet` | `streamlit run streamlit_app.py` |

The diagram's two **Store** arrows are two different write paths: chunks are embedded into the
vector store by `build_index` and simultaneously become `chunk` nodes in the evidence graph
(`evidence_graph.py:105-113`). The two **Retrieve** arrows are likewise distinct reads: cosine
search hits come from the store; each hit's `chunk_id` doubles as its `evidence_id`, resolvable in
the graph — that identity (`retriever.py:38`) is what stitches RAG output into constitution I-2.

---

## 3. The RAG, step by step

### 3.1 Index time (once per corpus)

1. **Parse** — `DocReader.read()` (`text_etl.py:99-109`) handles `md/txt/docx/pdf`. PDF text comes
   from `pypdf.extract_text()` (`:128-139`) — *text-layer extraction, not OCR* (see §6.1). Doc
   type (sop vs maintenance) is inferred from front-matter → filename keywords → content keyword
   balance.
2. **Chunk** — `Chunker.chunk()` (`text_etl.py:185-209`) windows each heading-bounded section in
   token space: target 175 tokens (tiktoken `cl100k_base`, whitespace fallback), 20-token overlap,
   never crossing a heading. Result: 934 chunks with stable ids `doc_<hash>__c<ordinal>`.
3. **Tag** — `TopicTagger` assigns topics (vibration, tool_wear, clamping, coolant, spindle,
   feed_speed) by keyword lists from `config/dataset.yaml`. These tags ride along as vector-store
   metadata and later drive the retriever's boost.
4. **Embed** — `build_index.py` validates a sample of chunks against the `SOPChunk` contract
   (`build_index.py:48-63`), then embeds all chunk texts with BGE (`normalize_embeddings=True`, so
   cosine = dot product). A deterministic `hashing_fallback` embedder exists for tests only and
   can never masquerade as BGE — the store records its embedder and `require_embedder` refuses
   mismatches (D14).
5. **Store** — `VectorStore.save()` persists ids + vectors + metadata (`doc_id`, `doc_type`,
   `citation` like `sop:doc_9b792f…§c0021`, `topic_tags`, `n_tokens`, full text) into one parquet.
   At 934 × 768 (~2.7 MB) brute-force is exact and fast; FAISS is the documented scale-up path.
6. **Graph** — `build_graph()` (`evidence_graph.py:96-150`) adds every chunk, doc, incident,
   sub-window (`SW_*`), video file, and failure-family node, with `video_matched` edges carrying
   `sync_provenance: constructed` (I-8) and build-time `linked_sop`/`linked_maintenance` edges
   marked `method="keyword_topic_build_time"` to distinguish them from runtime vector retrieval.

### 3.2 Query time (per incident)

7. **Query construction** (`IncidentRetriever.build_query`, `retriever.py:57-64`) — exactly the
   diagram's two green inputs, joined:
   `"CNC <failure family> diagnosis and corrective action; <sensor summary>; <clip summary>"`.
   - The *sensor summary* is computed, never generated: RMS trend across sub-windows, peak-activity
     interval, max kurtosis — from `sensor_features.parquet`, which is produced by the one feature
     path (I-3/D12).
   - The *clip summary* is the frozen VLM's output for the incident's linked clip, when
     `video_summaries.parquet` has one (wired in at `temporal/grounding.py:156-159`, comment "B-9:
     the real VLM summary joins the retrieval query").
8. **Search + re-rank** (`retriever.retrieve`, `:66-89`) — the query is embedded with the BGE
   query prefix, the store returns 3k candidates (optionally filtered by `doc_type`), and each hit
   gets `boosted_score = cosine + 0.05 × |hit topics ∩ failure-family topics|` using the
   `failure_to_topics` map from config. Top-k survive as `RetrievedEvidence` records whose
   `evidence_id == chunk_id`.
9. **Consumption point A — temporal grounding** (`src/temporal/grounding.py`): every 12-s
   sub-window becomes a contract-valid `AlignedTuple` whose `retrieved_text` is the top hit and
   whose `evidence_ids` = [window_id, top-2 chunk ids, video file]; any id that does not resolve
   in the graph **raises** (`grounding.py:76-78`) → `aligned_tuples.parquet`, run record
   `grounding_v1_*` with `evidence_resolution_rate`.
10. **Consumption point B — evidence selection / fusion v1** (`src/fusion/select.py`, decision
    D8): per incident, rank sensor windows by `max(encoder, heuristic)` anomaly, the clip by VLM
    confidence, documents by boosted cosine; verify every selected id resolves (I-2, raises
    otherwise); emit `evidence_bundles.parquet` and the decoder-facing text block
    `decoder_contexts.parquet` (`build_context`, `select.py:130-157`), which explicitly labels the
    video section "sync_provenance: constructed — no within-incident timestamps".
11. **Generation** (`src/explain/generate.py`): prompt = rules + full `ExplanationOutput` JSON
    Schema + allowed evidence ids + context block (`generate.py:44-67`). The llama.cpp provider
    decodes **under the GBNF grammar compiled from that same schema** (`grammar.py` — shape
    guaranteed by construction; pydantic re-validates cardinality; grammar quirks like
    no-underscore rule names and no bounded repetition are documented in-file from a reproduced
    llama.cpp crash). Greedy decoding, seed 20260702 (I-5).
12. **Guardrails** (`apply_guardrails`, `generate.py:97-121`) — after contract validation (gate
    G1), claims citing unresolvable evidence ids or spans overlapping no real sub-window are
    **dropped** into `unsupported_claims` (I-2); if nothing survives, the incident fails rather
    than emitting an ungrounded explanation. Out-of-order but grounded chains are deterministically
    re-sorted and flagged `chronology_repaired` (`:148-164`). The test split is refused outright
    (`generate_corpus` raises `PermissionError`, I-4, `:194-195`).
13. **Output** — the contract object plus the report-shaped dict land in `explanations.parquet`
    (mock and llm rows coexist per incident); a `decoder_<provider>_*` run record is appended with
    `schema_valid_rate`, guardrail drop counts, and latency.

### 3.3 Where the UI touches the RAG

`streamlit_app.py` ("CNC Incident Workbench") exposes the retriever live: the **SOP Evidence** tab
has a free-text box pre-filled by `default_retrieval_query(incident)` and runs a *real* vector
search on each edit, captioned with the store size and embedder name
(`streamlit_app.py:629-643`); build-time keyword-linked chunks are demoted to an expander so the
two retrieval generations are never conflated. The **AI Explanation** tab renders the decoder
report — mode chip distinguishing `REAL LLM (GBNF-constrained)` from `MOCK template`, per-claim
`[t_start → t_end]` spans with evidence ids, SOP linkage, corrective actions, and a warning panel
for guardrail-dropped claims (`:592-616`).

---

## 4. Artifact lineage (all present on disk, 2026-07-07)

```
raw text_manuals/ ──text ETL──▶ text_chunks.parquet (934)
                                   │ build_index (BGE, GPU)          │ build_graph
                                   ▼                                  ▼
                            vector_store.parquet            evidence_graph.json
                                   ▲ cosine + topic boost            ▲ resolve() (I-2)
sensor_features.parquet ──┐        │                                  │
subwindows.parquet        ├─▶ IncidentRetriever ──▶ aligned_tuples.parquet (grounding_v1)
video_summaries.parquet ──┘        │                                  │
                                   ▼                                  │
                        evidence_bundles.parquet + decoder_contexts.parquet (fusion_v1)
                                   │  GBNF decoder (Qwen2.5-7B GGUF) + I-2 guardrails
                                   ▼
                          explanations.parquet ──▶ workbench "AI Explanation" tab
```

---

## 5. Constitution & decision hooks active inside the RAG path

| Invariant / decision | Where it bites in this path |
|---|---|
| I-1 frozen backbone | VLM summarizer: `model.eval()`, `requires_grad_(False)`, `no_grad` (`summarizer.py:105-107,121`) |
| I-2 evidence-or-silence | graph `resolve()`; grounding and fusion raise on unresolvable ids; decoder guardrails drop violating claims |
| I-3 one feature path | sensor summaries templated from `src/features/vibration.py` outputs via `sensor_features.parquet` (D12 moved `spectral_bands`/`sliding_rms` here) |
| I-4 test quarantine | `generate_corpus(split="test")` → `PermissionError` |
| I-5 determinism | greedy decoding, fixed seed, run records with git_sha/config_hash on grounding, fusion, and decoder runs |
| I-8 sync provenance | `video_matched` graph edges, clip summaries, and the decoder context all carry `constructed` |
| I-9 constrained decoding | `grammar.explanation_grammar()` compiled from the contract's JSON Schema |
| D2 / D7 / D8 / D10–D14 | decoder model choice / NetworkX graph / deterministic fusion v1 / window convention / GPU-first / patch geometry / encoder tokens / BGE + brute-force store |

---

## 6. Divergences from the diagram (ranked)

1. **No SOP upload UI (capability #11).** `streamlit_app.py` contains no `st.file_uploader`;
   ingestion is a manual file drop + `python -m src.cli text` + re-running
   `build_index`/`evidence_graph`. The diagram's first box is a batch pipeline today, and adding a
   document also requires the two index rebuilds — nothing incremental exists.
   **OCR is not implemented**: `pypdf.extract_text()` reads the text layer only; a scanned SOP
   would silently yield empty chunks. If real scanned manuals are in scope, this needs an OCR
   fallback (e.g. tesseract) and a decision-log entry.
2. **Decoder is Qwen, not Gemma.** Deliberate (D2: Qwen2.5-7B-Instruct primary, Gemma-2-9B-It
   ablation). The diagram label survives only as the ablation row; no Gemma GGUF is staged.
3. **Chunk tagging is topic-keywords, not the 5-field schema.** The spec's M5 tags
   (`equipment, subsystem, step_number, alarm_code, operating_mode`) are not extracted; chunks
   carry `doc_type` + topic tags, and the `SOPChunk` contract is satisfied with those in its
   free-form `tags` dict (`build_index.py:56-58`). The retriever's payload-filter stage
   (spec M6: equipment ∧ operating_mode) is correspondingly reduced to an optional `doc_type`
   filter + topic boost.
4. **Two retrieval generations coexist.** Build-time keyword/topic linking
   (`assemble_incidents.TextRetriever`, family-level, cached) still populates
   `incidents.parquet`'s `sop_chunk_ids` and the graph's `linked_sop` edges; the runtime
   vector RAG is what grounding/fusion/decoder and the live UI use. The graph labels the old
   edges `keyword_topic_build_time`, and the UI separates them — but downstream consumers must
   not confuse the two (the eval `pct_with_sop_and_maint` metric still measures the *old* path).
5. **Vector store and graph are files, not services.** Brute-force parquet store (D14; Qdrant
   from the spec is absent, FAISS named as scale-up) and NetworkX JSON (D7; Neo4j a non-goal).
   Correct at 934 chunks; revisit only if the corpus grows orders of magnitude.
6. **Retrieval quality is not yet measured.** No gold `sop_chunk_ids` for the runtime path, so
   spec gate G10 (Evidence Recall@K) and M6's Recall@5 ≥ 0.8 remain unscored; current run records
   assert only *resolution* (G2), not *relevance*.
7. **Governance nit:** D15 (3B VLM substitution) is cited in `config/dataset.yaml:238`,
   `summarizer.py:5`, and `00_entry_report.md` ("decision log D1–D15"), but `docs/_sdd/decisions.md`
   ends at D14 — the D15 entry was never written. One-paragraph fix.

---

## 7. Self-evaluation

**Verified directly:** every module named above read in full this session
(`retrieval/{embeddings,store,search,retriever,build_index}.py`, `graph/evidence_graph.py`,
`fusion/select.py`, `explain/{generate,grammar,providers}.py`, `vision/summarizer.py`,
`temporal/grounding.py`, plus `text_etl.py` and UI panels); all 8 pipeline artifacts +
`models/gguf/Qwen2.5-7B-Instruct-Q4_K_M.gguf` confirmed present on disk; decision log D10–D14 read
in full; `runs.jsonl` at 20 records.

**Not verified (limits):** I did not execute the GPU paths (BGE embedding, VLM, llama.cpp) or
re-run the pipeline — runtime behavior is code-derived plus the run records and D14's timing note;
the "209 tests passed" figure is quoted from `00_entry_report.md` (2026-07-03), not re-run today;
retrieval *quality* (are the top-k chunks actually relevant?) is unmeasured by anyone yet, per
divergence #6; parquet contents were not opened row-by-row.
