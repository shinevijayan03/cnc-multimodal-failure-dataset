# TGFX Decision Log

Source: `C:/Users/Admin/Downloads/master_prompt.md`, section 0.

## D1 - Incident Window Span

Decision:
- Incident window is `[-60s, +30s]`.
- Sensor encoder consumes 12-second sliding sub-windows with stride 3 seconds.
- `important_sensor_interval` is expressed in incident-relative seconds.

Status:
- Accepted in user spec.
- Contract partial implemented in `contracts.core.SensorWindow`.

## D2 - Decoder LLM Naming

Decision:
- Primary decoder: Qwen2.5-7B-Instruct.
- Secondary/ablation: Gemma-2-9B-It.
- Use Q4_K_M GGUF through llama.cpp with GBNF grammar compiled from JSON Schema.

Status:
- Accepted in user spec.
- Not implemented in this iteration.

## D3 - Sensor Channel Naming

Decision:
- Canonical sensor channels are `ax`, `ay`, `az`.
- Derived features are computed artifacts from one feature path.

Status:
- Accepted in user spec.
- `SensorWindow` enforces exact `ax`, `ay`, `az` keys.

## D4 - Video Provenance Is Constructed

Decision:
- Stock video sync must be declared with `sync_provenance`.
- Alignment ledger and misalignment probe are required later.

Status:
- Accepted in user spec.
- `VideoClip.sync_provenance` is explicit and has no default.

## D5 - Circular Gold Intervals

Decision:
- Sensor gold intervals derive exclusively from sensor-side ground truth.
- Video intervals are reported separately.

Status:
- Accepted in user spec.
- Not implemented in this iteration.

## D6 - Root-Cause Taxonomy

Decision:
- Use five sub-causes: imbalance, misalignment, bearing_wear,
  mechanical_looseness, tool_wear_progression.

Status:
- Accepted in user spec.
- Implemented in `contracts.core.SubCause`.

## D7 - Evidence Graph Backend

Decision:
- Use NetworkX plus JSON-serialized graph for v1.
- Neo4j is a non-goal.

Status:
- Accepted in user spec.
- Not implemented in this iteration.

## D8 - Fusion Mechanism Honesty

Decision:
- v1 fusion is text-mediated with a learned evidence-selection head.
- Learned cross-attention fusion is P1 and droppable.

Status:
- Accepted in user spec.
- Not implemented in this iteration.

## D9 - Claim Extraction Is Structural

Decision:
- Claims are enumerated from `ExplanationOutput.chronological_evidence_chain`.
- No fuzzy claim-splitting NLP is required for core evaluation.

Status:
- Accepted in user spec.
- `ExplanationOutput` and `ChainClaim` are implemented.

## D10 - Window Convention Operationalization (Build Phase 1 gate)

Decision:
- The ETL incident window (currently ±8s around the detected event for the
  staged corpus) remains the *incident span* producer; it widens toward
  [-60, +30] only when source recordings are long enough.
- The encoder/grounding layer carves 12-second sub-windows (stride 3 s, per D1)
  from within the incident span; `contracts.core.SensorWindow` is the contract.
- The default *query window* for explanation generation is [-12s, 0s] relative
  to the event anchor (matches the target diagram).
- Where a recording cannot cover a convention (e.g. 20 s runs), the available
  span is used and recorded; no synthetic padding is invented.

Status:
- Approved by user 2026-07-03 at the audit review gate
  ("Approved" — see docs/architecture_audit/13_recommended_build_roadmap.md §First build phase).
- Implementation lands in Build Phases 2–3.

## D11 - GPU-First Execution Policy

Decision:
- All model components (encoder training/inference, embeddings, VLM, decoder
  LLM) always use the local GPU. CPU fallbacks may exist for tests only and
  must be marked as such.
- Any GPU limitation (VRAM, kernel, driver) is reported back to the user as a
  re-architecture input, not silently worked around.

Hardware baseline (probed 2026-07-03):
- NVIDIA GeForce RTX 3060, 12 GB VRAM, driver 595.79, CUDA 13.2 (WDDM).
- torch 2.6.0+cu124 installed; `torch.cuda.is_available() == True`.

Known implications (reported at Phase 1 gate):
- Qwen2.5-VL-7B fp16 (~15-16 GB) does not fit in 12 GB → Phase 7 must use an
  int4/AWQ-quantized 7B or the 3B variant; user decision scheduled at the
  Phase 7 entry gate. Constitution I-1 (frozen VLM) is unaffected by
  quantization.
- Decoder path per D2 (Q4_K_M GGUF via llama.cpp, ~4.7 GB for 7B) fits 12 GB
  alongside GBNF decoding.
- Encoder (Phase 4, PatchTST-scale) and BGE-base embeddings (Phase 5) fit
  comfortably.

Status:
- Approved by user 2026-07-03 ("use the local gpu always, report back issues
  with the gpu so that we can re architect to match the gpu").
