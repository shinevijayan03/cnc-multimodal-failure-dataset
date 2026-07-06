# 04 — Missing Implementation Backlog

| # | Missing Area | Expected Behavior | Current Evidence | Required Build | Complexity | Priority |
|---|---|---|---|---|---|---|
| B-1 | Decoder LLM + evidence-linked output | Gemma/Mistral/Qwen-Instruct emits `{failure_hypothesis, chronology[], evidence{sensor,video,documents}, sop_links, corrective_actions, confidence, uncertainties, unsupported_claims}` per contract, GBNF-constrained (I-9), every claim citing graph-resolvable ids (I-2) | contracts only; no `src/explain/` | provider abstraction (mock + local GGUF/llama.cpp), prompt template from aligned tuples, JSON-schema→GBNF compiler, guardrails, B1 free-text baseline | Deep | **P1** |
| B-2 | Evidence selection head + multimodal context builder | rank sensor intervals / clip summaries / SOP chunks across modalities with confidences; build the decoder context | deterministic retriever top-k only | `src/fusion/`: projection over Hvib + retrieval scores + VLM confidences; deterministic v1 selector; traceable bundle | Deep | **P1** (feeds B-1) |
| B-3 | Faithfulness audit over real outputs | attribution precision, unsupported-claim rate, temporal ordering, hallucination report, audit panel | fixture-only harness; placeholder AUROC/ECE/judge | real-output adapter into `compute_metrics` (I-6 freeze process), report writer, UI panel | Deep | **P2** |
| B-4 | UI completion | clickable evidence markers → highlight source; decoder explanation panel; audit panel; (bidirectional video sync = platform-limited, needs custom JS component) | one-way sync; grounded bars; no click-to-highlight | Streamlit selection events (`st.altair_chart on_select`) + panels; optional JS video component | Medium | **P2** |
| B-5 | SOP upload UI + OCR + 5-facet tagging | upload from the workbench → parse (OCR for scans) → chunk → tag equipment/subsystem/step/alarm/mode → embed → index + graph, with upload security tests | filesystem ingestion; topic tags only | `st.file_uploader` flow → text_etl reuse; OCR hook (e.g. tesseract) behind optional dep; metadata schema + tagger; path/size/type validation | Deep | **P3** |
| B-6 | Real PatchTST (or TimesNet) encoder | raw-patch transformer encoder option beating the AE baseline | AE over patch-feature tokens; config slot exists | `encoder.kind=patchtst` implementation, seeded, GPU; ratchet vs AE (I-10) | Deep | **P3** (needs gold labels for honest gating) |
| B-7 | predicted_sensor_state | per-window state label (normal/pre_failure/failure/post_alarm per `WindowPhase`) | field absent from producer | heuristic v1 from alarm_state+anomaly; learned later | Medium | P3 |
| B-8 | Sensor query tokens → frozen model | Hvib conditions the VLM/decoder ("sensor queries" in D2) | none | text-mediated v1 (sensor summary already in retrieval query; extend to decoder prompt) — token-level bridge is research | Deep/R | P4 |
| B-9 | Video summary in retriever query at grounding time | retrieval query includes clip summary | retriever supports `clip_summary` param; grounding doesn't pass it | one-line wiring + re-ground | Small | P2 (bundle with B-2) |
| B-10 | Gold mini-set (cross-cutting, science) | 20–40 val incidents human-labeled (sub-cause + spans) | weak scaffolding labels only | labeling workflow + storage; unblocks honest metrics for B-1/B-3/B-6 | Human effort | **P1 parallel** |
| B-11 | LLaVA-NeXT-Video comparison | second frozen VLM for comparison table | Qwen only | adapter reuse; VRAM check first | Medium | P4 |
| B-12 | Hardening/final compliance | full regression, security review (upload+LLM paths), dead-code pass, final matrices | per-phase records exist | fable_prompt Phase 9 artifacts | Medium | last |

## Deep Build Areas (required by prompt §C)
Real implementation needed: decoder prompt/output schema (B-1), evidence
selection head (B-2), faithfulness audit (B-3), SOP ingestion upload+OCR+
tagging (B-5), PatchTST path (B-6), UI evidence interaction (B-4).
Already really implemented (not cosmetic): temporal grounding layer,
synchronized sensor/video timeline (one-way), video summarization path,
vector store, evidence graph, retriever, regression tests.
