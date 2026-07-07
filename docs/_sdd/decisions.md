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

## D12 - Patch Geometry and Canonical Window Signal (Build Phase 3)

Decision:
- Patch tokens are 0.25 s slices with 0.125 s stride (50% overlap); at the
  staged 2 kHz rate a 12 s sub-window yields 95 patches of 500 samples.
  Incomplete tail patches are dropped, never padded (mirrors D10).
- The canonical per-window scalar-feature signal is the tri-axial magnitude
  sqrt(ax^2+ay^2+az^2) with its median removed (DC mounting offset), so RMS /
  kurtosis / variance / spectral bands reflect vibration, not the mount.
- Spectral energy uses 4 equal-width bands from 0 Hz to Nyquist
  (contract `SensorWindow.spectral_energy` fixes n=4).
- The heuristic anomaly score is delta/(1+delta) of the window RMS rise over
  the incident's earliest sub-window (feature_delta from the one feature
  path); it is a Phase 3 placeholder until the trained encoder (Phase 4).

Status:
- Adopted 2026-07-03 in Build Phase 3; implemented in
  `src/features/patching.py`, `src/features/vibration.py`
  (spectral_bands, sliding_rms moved from the ETL), and
  `src/tgfx/sensor_features.py`.

## D13 - Encoder Input Tokens and Diagnostic Labels (Build Phase 4)

Decision:
- The v1 sensor encoder consumes patch-feature tokens: per 12 s sub-window a
  (95 patches x 15 features) matrix - per patch and channel, RMS + 4 spectral
  bands from the one feature path (I-3). Raw-patch PatchTST input remains a
  config-selectable future `encoder.kind`.
- The training diagnostic target is the recovered run-level good/bad folder
  label (scripts/derive_quality_labels.py; real labels, every window inherits
  its run's label). This is a diagnostic, NOT KPI gate G3, which stays
  fixture-only until Phase 12 (I-6 untouched).
- GPU determinism (D11 + I-5) requires CUBLAS_WORKSPACE_CONFIG=:4096:8; the
  encoder module sets it before the first cuBLAS call.

Status:
- Adopted 2026-07-03 in Build Phase 4; implemented in `src/encoder/`;
  first run record: encoder_autoencoder_20260702_20260703T175903+0530
  (val AUROC 0.5798 vs heuristic 0.4170, deterministic across re-runs).

## D14 - Embedder and Vector Store (Build Phase 5)

Decision:
- Chunk embeddings use BAAI/bge-base-en-v1.5 (768-d, L2-normalized, CLS
  pooling via sentence-transformers) on the local GPU (D11), exactly matching
  the `SOPChunk` contract declaration. Queries get the BGE retrieval prefix.
- The vector store is exact brute-force cosine over normalized vectors,
  persisted as one parquet file that records its embedder name; search
  refuses mismatched embedders. At 934 chunks x 768 dims (~2.7 MB) an ANN
  index is unnecessary; FAISS (already installed) is the documented scale-up
  path if the corpus grows by orders of magnitude.
- A deterministic hashing embedder exists ONLY as a clearly named fallback
  (`hashing_fallback`) for tests and the model-less sample smoke path; stores
  built with it can never masquerade as BGE.
- Citation format: `<doc_type>:<doc_id>§<chunk_ordinal>` (e.g.
  `sop:doc_9b792f170d38§c0021`).

Status:
- Adopted 2026-07-03 in Build Phase 5; implemented in `src/retrieval/`
  (embeddings, store, build_index, search). Real-corpus index: 934 chunks
  embedded on the RTX 3060 in 6.24 s.
