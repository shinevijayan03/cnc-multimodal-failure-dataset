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
