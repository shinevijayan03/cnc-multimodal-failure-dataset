# 04 — Target Architecture Interpretation

Source: the four diagrams and the written target summary supplied by the user
on 2026-07-03, cross-referenced with `CLAUDE.md` (TGFX Constitution) and
`docs/_sdd/spec.md`. Items marked **(recommended extension)** are not in the
diagrams but are implied by the constitution.

## System intent

A **temporally grounded, evidence-linked multimodal failure explanation system**:
given an incident (vibration time-series + machine video + SOP/maintenance
documents), produce a chronological failure hypothesis in which **every claim
cites resolvable evidence IDs** and every time reference is incident-relative.

## Subsystems

### S1. Vibration sensor pipeline (diagram 1)

Raw vibration (vibration_x/y/z, RMS, spectral_energy) → select incident window
(t = -12s to t-0s before alarm) → **patch creation** (window → patch tokens) →
**trainable encoder** (PatchTST-style / TimesNet / 1D CNN) that learns
degradation signatures (RMS rise, spectral-band increase, abnormal variance) →
sensor outputs: `sensor_summary`, `anomaly_score`, `predicted_sensor_state`,
`important_sensor_interval`, evidence IDs. Embedding output **Hvib** feeds fusion.

Constitution constraint: feature math (RMS, spectral bands, kurtosis, variance)
must live only in `src/features/vibration.py` (I-3).

### S2. Video understanding pipeline (diagrams 2–3)

Machine video → clip extraction around the incident timeline → frozen VLM
(Qwen2.5-VL-7B-Instruct primary, LLaVA-NeXT-Video comparison — I-1: never
fine-tuned in v1; LoRA only after v1 gates + human approval) → clip summaries
("wobble", oscillation, tool breakage, smoke/sparks) with time span, confidence,
evidence ID. Embedding/summary output **Hvis** feeds fusion. Every clip carries
`sync_provenance` (I-8).

### S3. SOP / maintenance document pipeline (diagram 3)

Documents → text extraction → semantic chunking → embeddings → metadata tags
(equipment, subsystem, step number, alarm code, operating mode) → **Vector DB**
+ **Evidence Graph** storage. Retrieved chunk output **Htext** feeds fusion,
with SOP section citation and evidence ID.

### S4. Retriever (diagrams 2 & 4)

Takes a **sensor + video query** (constructed from sensor summary and clip
summary), retrieves SOP chunks via vector similarity + evidence-graph relations
+ metadata filters + incident context; outputs grounded SOP evidence.

### S5. Temporal grounding layer (diagram 3)

Timestamp normalization → logical incident time → **aligned tuples**
`<window_id, sensor_summary, clip_summary, retrieved_text, alarm_state,
mode_state, ...>` → chronological-order validation → multimodal evidence
prepared for fusion. The existing contract `contracts/core.py::AlignedTuple`
is the schema for this output.

### S6. Multimodal fusion layer (diagrams 2 & 4)

Joint feature space over Hvib + Hvis + Htext; cross-modal correlation /
cross-attention; outputs a temporally grounded multimodal evidence bundle.

### S7. Evidence selection head (diagram 3)

Scores and selects the strongest sensor intervals, video clips, and SOP chunks
(top-K, confidence) for the generator prompt.

### S8. Decoder LLM explanation generation (diagram 3)

Decoder LLM (Gemma / Mistral / Qwen Instruct) emits: failure label,
chronological evidence chain, SOP linkage, confidence, uncertainty, corrective
action. Output schema is `contracts/explanation.py::ExplanationOutput`.
Constitution: emission via **GBNF grammar compiled from the JSON Schema** (I-9);
free-text only in baseline B1. Every claim must carry >= 1 resolvable
evidence_id (I-2).

### S9. Evaluation and faithfulness audit (diagram 3)

Failure detection F1/AUROC; root-cause top-1/top-K; per-modality evidence
precision; temporal IoU; temporal ordering accuracy; evidence Recall@K;
attribution precision/recall; unsupported claim rate; temporal hallucination
rate; calibration (ECE); human usefulness rubric. All metrics produce run
records (I-5, I-7); metric code freezes after meta-tests (I-6); test split
quarantined (I-4).

### S10. Demo / UI layer **(recommended extension)**

The diagrams end at "temporally grounded output" + audit; a runnable demo
(extend the existing Streamlit explorer with an "Explain" flow) is a
recommended extension for user testing at phase gates.

## Interpretation notes / discrepancies to resolve

1. **Window length.** Diagram 1 says t=-12s..0s; `contracts/core.py::SensorWindow`
   requires 12.0s sub-windows *inside* a [-60, +30] incident span; the current
   ETL carves ±8s windows (`config windowing pre/post_event_s: 8.0`). These
   three conventions must be reconciled in the temporal-grounding build phase
   (Decision Log entry required — I-12 escalation if ambiguous).
2. **VLM choice.** Diagram 3 lists "LLaVA-NeXT-Video or Qwen2.5-VL" with
   optional LoRA "(if needed after testing)"; the constitution makes Qwen2.5-VL
   primary and forbids LoRA in v1 (I-1). The constitution wins.
3. **Spectral bands.** Contracts fix `spectral_energy` at exactly 4 bands;
   the diagrams don't specify a count. Treat 4 as the binding value.
4. **Fusion depth.** "Cross-modal correlation / cross-attention" can be a
   trainable cross-attention block or a deterministic correlation baseline.
   v1 should start with the deterministic baseline (frozen backbone, I-1) and
   add trainable fusion behind a config flag.
