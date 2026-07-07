# 01 — Architecture Ingestion (4 diagrams)

## D1 — System overview
Interleaved vibration + video ("What caused the failure?") → PatchTST/TimesNet
encoder → sensor summary ("RMS rise…") → **Retriever** ← Frozen Vision-LLM
(video → "Wobble") ← Vector Database + **Knowledge Graph** → **Decoder LLM** →
4-step chronological failure hypothesis (t=18–27 RMS rise; t=24 wobble;
t=29 pressure after instability; SOP §4.2 bearing wear).

## D2 — Grounding + decoder pipeline
Vibration → TimesNet; video → **Timestamp Normalization** → **Logical incident
time** → **Temporal Grounding Layer** producing aligned tuples
`<window_id, sensor_summary, clip_summary, retrieved_text, alarm_state,
mode_state>` → **LLaVA-NeXT-Video or Qwen2.5-VL** (frozen; "LoRA if needed
after testing"; sensor queries) + **Evidence Selection Head** → prompt →
**Decoder LLM: Gemma/Mistral/Qwen Instruct** (failure label, chronological
evidence chain, SOP linkage, corrective action) → Failure-hypothesis output ↔
**Evaluation and Faithfulness Audit**. SOP text → embedding encoder, semantic
chunking → tag chunks with **equipment, subsystem, step number, alarm code,
operating mode** → Vector Store + Evidence Graph ← Retriever.

## D3 — SOP RAG
**UI for uploading SOP documents** → Document Processor (**parsing, OCR,
chunking, tagging**) → **Embedding Generation: BGE** → Vector Store + Evidence
Graph → Retriever, queried by sensor summary ("RMS rise..") and video summary
("Wobble..") → **Decoder LLM: Gemma** → Output.

## D4 — Sensor pipeline
Raw vibration (x, y, RMS, spectral energy) → incident window **t=−12s..0s
before alarm** → patch creation → **PatchTST trainable encoder** learning
degradation signatures (RMS rise, spectral-band increase, abnormal variance)
→ sensor output: `sensor_summary, anomaly_score, predicted_sensor_state,
important_sensor_interval` → multimodal fusion / evidence selection.

## Required-capability list (union of diagrams + fable_prompt §Target)
1 interleaved sensor/video ingestion · 2 incident-window selection (−12..0) ·
3 patch creation · 4 PatchTST/TimesNet encoder · 5 degradation-signature
learning · 6 sensor summary + anomaly_score + predicted_sensor_state +
important interval · 7 frozen VLM video summaries · 8 video evidence
intervals · 9 timestamp normalization + logical incident time · 10 aligned
tuples (exact 6-field shape) · 11 **SOP upload UI** · 12 parsing/**OCR**/
chunking · 13 semantic tagging (equipment/subsystem/step/alarm/mode) ·
14 BGE embeddings · 15 vector store · 16 evidence/knowledge graph ·
17 retriever (sensor+video queries) · 18 sensor query tokens into frozen
model · 19 evidence selection head · 20 decoder LLM (Gemma/Mistral/Qwen)
with failure hypothesis/chronology/SOP linkage/corrective actions ·
21 faithfulness audit (attribution, temporal correctness, unsupported
claims, report) · 22 final UI (synchronized sensor/video timelines,
evidence-linked output, clickable evidence).

Conflicts with the repo constitution (constitution wins, recorded):
D2 mentions LoRA — I-1 forbids v1 fine-tuning; D2/D1 say Qwen2.5-VL-**7B** —
D15 substitutes 3B for the 12 GB GPU (D11); diagram window −12..0 vs contract
12 s sub-windows — reconciled by D10 (approved).
