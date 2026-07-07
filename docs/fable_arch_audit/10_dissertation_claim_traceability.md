# 10 — Dissertation (Mid-Sem Report) Claim → Codebase Traceability + Gap Register

**Date:** 2026-07-07 · **Source ingested:** `2024AA05583_Mid-Sem.pdf` (18-Jun-2026), all 17 pages
**Tree:** `codex/complete-pending-phases` @ `f20282a` · artifacts verified on disk this session
**Legend:** ✅ realized · 🟡 partial (works, narrower than claimed) · ❌ missing

---

## 1. Abstract-level claims

| # | Report claim | Status | Where realized | Tell the professor |
|---|---|---|---|---|
| C1 | Output is a structured explanation (failure hypothesis, chronology, evidence, SOP linkage, confidence, uncertainty, corrective action), not "bearing failure happened" | ✅ | `contracts/explanation.py` (`ExplanationOutput`, 1–8 ordered `ChainClaim`s, each ≥1 evidence id) → `src/explain/generate.py` → `explanations.parquet`; rendered in AI Explanation tab; exported via ⬇ Evidence Report | "The abstract's exemplar JSON is the literal Pydantic contract; the decoder cannot emit anything else because the GBNF grammar is compiled from this schema (I-9)." |
| C2 | Temporally aligned multimodal evidence (sensor + video + SOP) around an incident timeline | ✅ | `src/temporal/grounding.py` → `aligned_tuples.parquet` (6-field tuple exactly as report §3); Build-C global clock in the UI | Show the aligned-tuples expander + Play-through |
| C3 | Key hypothesis: temporal alignment + fusion → fewer hallucinations than vision-only / sensor-only / late-fusion RAG | 🟡 mechanism built, **comparison unproven** | Guardrails (I-2) drop ungrounded claims; grounding/fusion exist. **Baselines B1–B4 do not exist**; §6.1 comparison table still blank | "The machinery to test the hypothesis is in place; baseline runs are the next phase — the report itself marks the table 'intentionally left blank'." |
| C4 | Hybrid dataset (real + synthetic) because no public benchmark exists | 🟡 | Real Bosch-style CNC CSVs + real manuals + stock clips assembled by `src/etl/`; **no synthetic sub-cause generator yet**; labels are weak hash-derived scaffolding, declared in README + manifest (`weak_signal_derived_not_ground_truth`) | Be upfront: demo-scale hybrid, curation pending |
| C5 | Frozen video-language backbone; train only lightweight sensor encoder / projection / selection head | ✅ frozen + 🟡 trainables | VLM frozen (I-1, `summarizer.py` no_grad/eval); sensor encoder trained (`src/encoder/`); selection head is deterministic v1 (D8) — projection adapter & learned head are P1 | "Constitution I-1 makes freezing non-negotiable; fusion honesty is logged as D8" |
| C6 | LLM used via structured, evidence-constrained prompts | ✅ | `generate.py` prompt: schema + allowed evidence ids + "cite only the evidence ids above"; GBNF-constrained greedy decoding | Show the decoder context expander — the exact prompt payload |

## 2. Module table (report §1) → code

| Report module | Status | Code |
|---|---|---|
| Infrastructure & runtime | ✅ | `config/dataset.yaml` + typed loader; GPU-first policy D11 (RTX 3060 baseline probed) |
| Data ingestion (3 sources, IncidentTuple) | ✅ | `src/etl/{sensor,video,text}_etl.py`; `contracts.core.IncidentTuple`; sample validated in `build_index`/grounding |
| Vibration encoder (PatchTST) | 🟡 | `src/encoder/torch_ae.py` — autoencoder over patch-feature tokens (95×15, D12/D13), val AUROC 0.5798 (run record). Raw-patch PatchTST = config-selectable future kind |
| Video pre-processing (frozen LLaVA/Qwen-VL) | 🟡 | Qwen2.5-VL-3B done (`video_summaries.parquet`); LLaVA-NeXT comparison ❌ |
| SOP document processing | ✅ | `text_etl` → chunks; `retrieval/build_index` → BGE vectors; graph nodes |
| Semantic retrieval | ✅ | `retrieval/retriever.py` (sensor+video query, cosine + topic boost) |
| Evidence graph | ✅ | `graph/evidence_graph.py` NetworkX (D7), `resolve()` backs I-2 |
| Temporal grounding (core novelty) | ✅ | `temporal/grounding.py`, contract-valid `AlignedTuple`s, chronology enforced |
| Evidence-conditioned fusion | 🟡 | `fusion/select.py` deterministic v1 (D8); learned head pending |
| Explanation generation (Gemma) | ✅ (model swapped) | `explain/` — Qwen2.5-7B GGUF + GBNF (D2 supersedes Gemma; Gemma-2-9B named ablation) |
| Evaluation & metrics | 🟡 | `src/eval/` fixture harness + meta-tests + 20 run records; dataset-quality gate PASS. Real faithfulness verification on generated outputs ❌ (verifier exists for fixtures only) |
| Streamlit UI (view/run/audit/rate) | 🟡 | Workbench: view ✅, evidence audit ✅, export ✅; **pipeline-run button ❌, 1–5 rating persistence ❌** |

## 3. Technical specifications (report §4) → reality

| Spec | Reality |
|---|---|
| One equipment + one failure family, incident-centred windows | ✅ CNC mill; abnormal-vibration family with D6 5-sub-cause taxonomy in contracts |
| Sensor-clocked timeline, t=0 = alarm | ✅ t=0 = detected event; one global clock (Build-C) |
| PatchTST-style transformer | 🟡 see encoder row above |
| Frozen Qwen2.5-VL or LLaVA | 🟡 Qwen-3B only (D11 VRAM: 7B fp16 doesn't fit 12 GB) |
| Qdrant vector DB | changed: brute-force parquet store (D14; exact at 934 chunks; FAISS scale-up path) |
| Evidence graph JSON/NetworkX, Neo4j TBD | ✅ NetworkX; Neo4j declared non-goal (D7) |
| Decoder "Qwen3-VL-Instruct or Gemma 4-31B" | changed: Qwen2.5-7B-Instruct Q4_K_M (D2 — report names a nonexistent model size; decision log corrects it) |
| Structured JSON + human-readable output with cited evidence IDs | ✅ both shapes in `explanations.parquet` |
| Single local GPU, quantized | ✅ D11: GGUF decoder ~4.7 GB, BGE, VLM-3B bf16 all fit 12 GB |
| Same frozen test set for all baselines; uniform claim extraction | 🟡 test split quarantined (I-4 enforced in code); baselines pending; claim extraction is structural (D9) |

## 4. Dataset claims (report §5) vs actual

| Target | Actual | Status |
|---|---|---|
| Schema §5.1 (incident_id, t −60..+30, ax/ay/az, sop/maintenance chunk ids, labels) | `incidents.parquet` matches field-for-field except window = ±8 s (staged 20 s runs; D10 rules span widening) | 🟡 |
| 2K video clips | 20 clips | ❌ scale |
| 72 h sensor | 7.56 h | ❌ scale |
| ~900-page text corpus | ~319 pages-equivalent, 934 chunks | ❌ scale |
| Splits 250–400 / 60–80 / 80–120 / 50–80 | 1192 / 255 / 170 / 85 (grouped, seeded, quarantined) | 🟡 different scheme, mechanics ready |
| Gold labels for evaluation | weak hash-derived labels only | ❌ curation pending |
| Benchmark suites (VidHalluc etc.) | not integrated | ❌ |

## 5. Evaluation metrics (report §7) → harness

All metric *names* exist in `src/eval/metrics.py` and every run appends to `docs/_eval/runs.jsonl`
(I-5/I-7). Status: interval IoU, attribution precision/recall, unsupported-claim rate,
wrong-time rate, schema-valid rate — real implementations, **exercised on hand fixtures, not yet
on generated explanations**. AUROC/ECE/macro-F1 are documented placeholders. Detection AUROC has
one real run (encoder 0.5798 val, diagnostic only per D13).

## 6. "Which part of the app realizes which claim" — one-line demo pointers

| Claim | Point at |
|---|---|
| Temporal grounding novelty | Play-through + timeline + aligned-tuples expander |
| Evidence-or-silence (I-2) | AI tab guardrail warning + `evidence_ids` on every claim |
| Frozen VLM | VLM chip under video panel |
| Trainable encoder | encoder-anomaly chip + sub-window features table |
| RAG | SOP tab live query box |
| Constrained decoding | mode chip "REAL LLM (GBNF-constrained)" |
| Structured output | ⬇ Export Evidence Report JSON |
| Test-set discipline | pick a test-split incident → "quarantined (I-4)" |
| Reproducibility | `docs/_eval/runs.jsonl` (20 records, git_sha/config_hash/seed) |

## 7. Gap register (what is missing, ranked by dissertation risk)

1. **Baselines B1–B4 + comparison table (§6.1)** — the hypothesis (C3) is untestable until these run. No `run_baseline.py`. *Highest priority; report timeline puts this in the 22-Jun→27-Jul phase.*
2. **Faithfulness evaluation on real outputs** — verifier (`verify_sensor`) + judge stub exist for fixtures; not yet wired to `explanations.parquet`. Metrics §7 can't be filled for the real system without it. Includes gold intervals/evidence (D5 protocol) — currently none.
3. **Dataset scale + label curation** — weak hash labels; 20 clips; no synthetic sub-cause generator (D6 signatures); misalignment probe (G9) unbuilt.
4. **PatchTST proper + learned selection head + projection adapter** — current encoder is an autoencoder over patch features (D13); trainables narrower than report §4.
5. **LLaVA-NeXT-Video comparison row** — needed for report §6.1 B1b.
6. **UI: pipeline-run button + 1–5 rating persistence** (report's Streamlit module spec) — viewing/audit/export done.
7. **SOP tag schema** — topic keywords instead of equipment/subsystem/step/alarm/mode; retrieval metadata filtering correspondingly reduced.
8. Minor: no SOP upload UI / OCR; Qdrant/Neo4j deliberately replaced by file-based equivalents (D14/D7 — defensible, present as decisions, not gaps).

**Honest framing for the viva:** phases marked "Done" in report §9 through "Temporal Alignment
and Multimodal Tuple Construction" are demonstrably real in code and on screen; the current
build has also pre-delivered parts of the 22-Jun→27-Jul phase (fusion v1, decoder, GBNF).
What remains is exactly the report's own remaining plan: baselines, quantitative evaluation,
ablation, and dataset statistics.
