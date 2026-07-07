# 09 — Professor Demo Guide: Architecture Realization + Step-by-Step Demo Script

**Date:** 2026-07-07 · branch `codex/complete-pending-phases` @ `f20282a`
**App:** `streamlit run streamlit_app.py` → http://localhost:8501 (verified healthz 200 this session)
**Companion docs:** `08_rag_implementation_and_diagram_realization.md` (RAG deep-dive),
`10_dissertation_claim_traceability.md` (Mid-Sem report claim → code map + gaps).

---

## Part A — How each attached architecture diagram is realized

### A.1 System overview (Figure 1 sketch: sensor+video → PatchTST / Frozen VLM → Retriever → Decoder LLM → 4-step chronology)

| Diagram element | Realization | Show the professor |
|---|---|---|
| Interleaved vibration/video data | `data_pipeline/data_raw/` staged corpus → `src/etl/` (sensor/video/text ETL) → `incidents.parquet` (1,702 incidents) | Sidebar artifact table in the app |
| PatchTST/TimesNet encoder, "RMS Rise.." | `src/tgfx/windows.py` (12 s sub-windows, stride 3 s, D10) → `src/features/` patch features (D12) → `src/encoder/` trained autoencoder anomaly scores (D13) → deterministic sensor summaries (`retriever.sensor_summary_text`) | "Sub-window features" expander + encoder chip |
| Frozen Vision LLM, "Wobble.." | `src/vision/summarizer.py` — frozen Qwen2.5-VL-3B (I-1: eval, no_grad; 3B per GPU decision D11/D15) → `video_summaries.parquet` | VLM chip + caption under the video panel |
| Vector Database + Knowledge Graph | `src/retrieval/store.py` (BGE vectors, 934 chunks) + `src/graph/evidence_graph.py` (NetworkX, `evidence_graph.json`) | Live retrieval box; `python -m src.graph.evidence_graph --resolve <id>` |
| Retriever | `src/retrieval/retriever.py` — query = failure family + sensor summary + VLM clip summary; cosine + topic boost | SOP Evidence tab, editable query |
| Decoder LLM | `src/explain/` — Qwen2.5-7B GGUF + GBNF grammar (I-9, D2; diagram's "Gemma" superseded by D2) | AI Explanation tab, mode chip |
| Orange output box (chronology 1–4) | `contracts.ExplanationOutput` → `explanations.parquet` → chronology list with per-claim `[t_start → t_end]` + evidence ids | AI Explanation tab |

### A.2 Grounding + decoder pipeline (Figure 1 of report)

| Element | Realization |
|---|---|
| TimesNet/Timestamp Normalization/Logical incident time | Event-anchored incident-relative clock (t=0 = detected event); Build-C unified one global clock across video, sensor chart, timeline (`src/ui/workbench.py` `PlaybackState`, `video_sync_spec`) |
| Temporal Grounding Layer → `<window_id, sensor_summary, clip_summary, retrieved_text, alarm_state, mode_state>` | `src/temporal/grounding.py` emits **exactly this 6-field tuple** as `contracts.AlignedTuple` → `aligned_tuples.parquet`; chronology validated; every evidence_id resolves in graph or it raises (I-2) |
| LLaVA-NeXT-Video or Qwen2.5-VL (frozen; LoRA if needed) | Qwen2.5-VL-3B frozen; **LoRA forbidden in v1 by constitution I-1**; LLaVA comparison not built (baseline gap) |
| Evidence Selection Head | `src/fusion/select.py` — deterministic v1 per decision D8 (trainable head is P1): sensor by anomaly score, video by VLM confidence, docs by boosted cosine; builds the decoder prompt context |
| Decoder LLM: Gemma/Mistral/Qwen | Qwen2.5-7B-Instruct Q4_K_M via llama.cpp, GBNF-constrained (D2/I-9); MockProvider as deterministic baseline |
| Failure hypothesis output + Evaluation and Faithfulness Audit | Report dict (hypothesis/chronology/evidence/sop_links/corrective_actions/confidence/uncertainties/unsupported_claims); audit = I-2 guardrails (drop unresolvable/out-of-span claims) + `src/eval/` fixture harness; full faithfulness verifier is a remaining phase |
| SOP path (bottom): chunk semantically → tag with equipment/subsystem/step/alarm/mode → Vector Store + Evidence Graph | `src/etl/text_etl.py` chunking + topic tags → `build_index` (BGE) + graph nodes. **Tag schema divergence:** topic keywords, not the 5-field schema (gap #3 in doc 08) |

### A.3 SOP RAG diagram — fully covered in `08_rag_implementation_and_diagram_realization.md` §2–§3. One-line summary: all boxes real except the upload UI (file-drop + `python -m src.cli text` instead) and Gemma→Qwen (D2).

### A.4 Sensor pipeline (raw vibration → incident window −12..0 → patches → PatchTST → signatures → sensor output)

| Element | Realization |
|---|---|
| Raw input `vibration_x/y, RMS, spectral_energy` | Canonical `ax/ay/az` (D3); RMS/spectral are **computed** by the single feature path `src/features/vibration.py` (I-3), never stored as input |
| Select incident window t=−12..0 | D10: incident span ±8 s (staged 20 s runs); 12 s sub-windows stride 3 s carved by `src/tgfx/windows.py`; [−12,0] is the default decoder query window |
| Patch creation | `src/features/patching.py` — 0.25 s patches, 50% overlap → 95 patches/sub-window (D12) |
| Encode with PatchTST (trainable) | `src/encoder/torch_ae.py` — trained autoencoder over 95×15 patch-feature tokens (D13); raw-patch PatchTST is a config-selectable future `encoder.kind`. Run record: val AUROC 0.5798 vs 0.4170 heuristic |
| Learn degradation signatures (RMS rise, spectral band, variance) | The 15 features per patch are RMS + 4 spectral bands per channel from the one feature path; anomaly = reconstruction error |
| Sensor output: `sensor_summary, anomaly_score, predicted_sensor_state, important_sensor_interval` | `sensor_features.parquet` has all four: templated summary, `anomaly_heuristic`+`anomaly_encoder`, `alarm_state` (pre_event/event_in_window/post_event), `important_start_s/important_end_s` |
| Used for multimodal fusion & evidence selection | Exactly what `src/fusion/select.py` consumes |

---

## Part B — Demo script (15–20 min, in order)

### B.0 Setup (before the professor arrives)
```bash
cd "e:\1.Final-Year-Project-2026\4. demo-old\cnc-multimodal-failure-dataset"
streamlit run streamlit_app.py          # → http://localhost:8501
```
All artifacts are pre-built; nothing needs re-running. If the page shows "No incidents.parquet",
run `python -m src.cli all` first. GPU paths (BGE/VLM/decoder) are only needed if you want to
*rebuild* artifacts live; browsing uses the saved parquets. (Live retrieval box does embed the
query — needs the BGE model; falls back with a clear message if the store/embedder mismatch.)

### B.1 Open — the data foundation (2 min)
1. Sidebar: artifact table — incidents (1,702), sensor windows, text chunks (934), video index (20 clips), plus the derived artifacts.
2. Say: *"Everything downstream is built from these four Parquet contracts; the build is one CLI: `python -m src.cli all`, then per-phase module CLIs. Grade: MVP PASS (`eval_report.md`)."*

### B.2 Pick an incident (1 min)
3. In "Choose an incident", pick a **train/val** incident (test rows show encoder scores as "quarantined (I-4)" — that itself is worth showing later).
4. Point at the status chips: run quality label (real good/bad folder label), encoder anomaly (real trained model), sub-window count, split.

### B.3 The shared incident clock — Build-C (3 min) ← *the temporal-grounding novelty on screen*
5. Press **▷ Play-through**. Narrate: video panel, sensor time-series cursor, and the Temporal Alignment Timeline all advance on **one global clock**; t=0 is the detected event.
6. Click a **Jump to evidence** pill → every view seeks to that span together.
7. Timeline rows = SENSOR / VIDEO / SOP / CLAIMS bars, each an evidence span in incident-relative seconds. Say: *"This is Figure 1's 'logical incident time' made concrete."*

### B.4 Sensor path — encoder outputs (2 min)
8. Open **"Sub-window features"** expander: per 12 s sub-window RMS, kurtosis, spectral bands, heuristic + encoder anomaly, important interval. Say: *"Diagram 4's sensor output tuple, computed by one feature path (constitution I-3), scored by the trained encoder (D13)."*

### B.5 Video path — frozen VLM (2 min)
9. Under the video: chip `VLM · Qwen/Qwen2.5-VL-3B-Instruct · conf …` + labels + one-sentence summary. Say: *"Frozen backbone (I-1) — no gradient ever touches it; sync provenance is declared 'constructed' everywhere (I-8)."*

### B.6 RAG live — retriever (3 min)
10. **SOP Evidence** tab: the query box is pre-filled from the incident (failure family + real sensor summary). Show top-4 hits with real cosine scores and citations (`sop:doc_…§c0021`).
11. **Edit the query live** (e.g. type "bearing lubrication interval") → hits change. Say: *"BGE embeddings over 934 chunks, brute-force cosine, topic-boost re-ranking — diagram 3's retriever."*
12. Open "Chunks linked at dataset build" expander: *"the old keyword generation, kept separate so the two are never conflated."*

### B.7 Grounding + fusion — how parts come together (3 min)
13. **"Temporal grounding · N aligned tuples"** expander: the exact `<window_id, sensor_summary, clip_summary, retrieved_text, alarm_state, mode_state>` tuples from Figure 1, contract-validated, every evidence id resolving in the evidence graph.
14. **"Evidence selection · fusion v1"** expander: ranked items across all three modalities + **the exact decoder context block**. Say: *"This text is literally what the LLM receives — nothing hidden."*

### B.8 Decoder output — the abstract's exemplar, generated (3 min)
15. **AI Explanation** tab: mode chip (`REAL LLM (GBNF-constrained)` or `MOCK template`), failure hypothesis, **chronological evidence chain with per-claim time spans and clickable evidence ids**, SOP linkage, corrective action, uncertainties.
16. Say: *"Schema validity is guaranteed by construction — the llama.cpp grammar is compiled from the same Pydantic contract (I-9). Claims citing unresolvable evidence or alien time spans are dropped by guardrails into `unsupported_claims` (I-2) — you can see the warning panel when that happened."*
17. **⬇ Export Evidence Report** → JSON download; open it to show the machine-evaluable output shape from report §3.

### B.9 Governance close (1 min)
18. Show `docs/_eval/runs.jsonl` (20 records — every number traceable, I-5/I-7), `CLAUDE.md` constitution, `docs/_sdd/decisions.md` D1–D14.
19. Optional terminal one-liners if asked for proof of the non-UI path:
```bash
python -m src.retrieval.search --query "spindle bearing vibration" --k 3
python -m src.graph.evidence_graph --resolve <chunk_id_from_hits>
python -m src.explain.generate --provider mock --limit 3 --no-write
pytest -q          # full suite
```

### Suggested talk-track sentence per diagram
- Diagram 1: *"Left-to-right on the slide is bottom-to-top in the app: raw data in the sidebar, encoder + VLM as chips, retriever in the SOP tab, decoder in the AI tab."*
- Diagram 2: *"The yellow Temporal Grounding box is the aligned-tuples expander; the tuple fields on the slide match the parquet columns one-for-one."*
- Diagram 3: *"The RAG loop runs live — type any query."*
- Diagram 4: *"The sensor tuple on the slide is the sub-window features table."*

---

## Part C — Failure modes during a live demo (know these)

| Symptom | Cause / fix |
|---|---|
| Test-split incident shows "quarantined (I-4)" | By design — pick train/val; *say so proudly* |
| Live retrieval box says index missing / embedder mismatch | `python -m src.retrieval.build_index` (needs GPU for BGE) |
| AI tab shows MOCK not REAL LLM | llm rows exist only where `--provider llama` was run; mock is the always-available deterministic baseline — demo either, the chip is honest |
| Video missing for an incident | 20 clips are label-matched with reuse; some incidents show "no linked video" — sensor evidence still renders (that is the video-silent path) |
| 🎬 DEMO incident in the dropdown | Simulated reference-UI scenario; everything marked with `demo` chips — use only to show the target UX, not as real data |
