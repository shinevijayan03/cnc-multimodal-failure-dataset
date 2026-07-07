# 07 — Deep-Build Required Areas

Prioritized register of areas needing substantial new engineering (not
config/parameter changes). Ordering follows dependency + risk, and respects
constitution I-11 (≤ ~600 changed lines per branch → each area splits into
multiple branches).

---

## DB-1 Sensor patching + feature extension

- **Why needed:** target S1 requires patch tokens and the 4-band
  `spectral_energy` demanded by `contracts/core.py::SensorWindow`.
- **Current evidence:** `src/features/vibration.py` has rms/variance/kurtosis
  only; sensor ETL computes RMS separately in numpy (`EventDetector._sliding_rms`).
- **Missing:** `spectral_bands()` in the one feature path; patcher
  (window → fixed-length patch tokens); 12s sub-window carver aligned to the
  contract's [-60,+30] convention.
- **Data needed:** existing per-incident waveform parquets (present, 1702 incidents).
- **Complexity:** Medium. **Risk:** I-3 violation if math is duplicated —
  refactor ETL RMS usage to import from `src/features/vibration.py`.
- **Test strategy:** unit tests with synthetic sinusoids (known band energy);
  meta-test that ETL and feature-path RMS agree.
- **Recommended phase:** Build Phase 3. **DoD:** patches + 4-band features
  produced deterministically for every incident window; single import path.

## DB-2 Trainable sensor encoder (Hvib)

- **Why:** S1 encoder learning degradation signatures; Hvib for fusion.
- **Current evidence:** none (T-10/T-11 not started).
- **Missing:** encoder abstraction, lightweight baseline (1D CNN or linear
  patch encoder) first, optional PatchTST integration, training loop with
  `--seed` (I-5), run records, deterministic inference mode.
- **Data needed:** patches from DB-1 + weak labels for pretext task; curated
  gold mini-set for validation.
- **Complexity:** Large (introduces torch, GPU-optional path).
- **Risk:** weak labels → the encoder may learn scaffolding artifacts; document
  as weak-supervision and gate on val only.
- **Test strategy:** shape/determinism tests; overfit-one-batch sanity; val
  anomaly-score AUROC vs heuristic baseline (ratchet I-10).
- **Phase:** 4. **DoD:** `Hvib` embeddings + anomaly_score reproducible with
  seed; run record appended.

## DB-3 Embeddings + Vector DB + SOP metadata

- **Why:** S3 storage layer; SOPChunk declares BGE-base-en-v1.5/768.
- **Missing:** embedding interface (local sentence-transformers or API-free
  fallback), persistent vector store (recommend SQLite-backed or FAISS/Chroma
  local — decision-log entry required), richer metadata tagging.
- **Complexity:** Medium. **Risk:** dependency weight; offline determinism.
- **Test strategy:** round-trip persist/search; recall@K on seeded queries;
  metadata filter tests.
- **Phase:** 5. **DoD:** `text_chunks` searchable by vector + metadata with
  evidence IDs.

## DB-4 Evidence graph + runtime retriever

- **Why:** S4; retrieval must combine vector hits, graph relations, filters,
  and incident context; feeds Htext and the I-2 evidence resolution path.
- **Current evidence:** flat `alignment_ledger.jsonl` only.
- **Missing:** node/edge schema (sensor window, video clip, SOP chunk, failure
  family, mode), graph store (start: networkx + JSON persistence), query API,
  sensor+video query construction.
- **Complexity:** Large. **Risk:** over-engineering; keep v1 graph minimal.
- **Test strategy:** graph integrity (every incident's evidence IDs resolve —
  directly supports I-2), retrieval ranking tests with known-relevant chunks.
- **Phase:** 6. **DoD:** `retrieve(incident_context) -> [SOPChunk + evidence_id]`
  with graph-backed resolution.

## DB-5 Video clip summaries via frozen VLM

- **Why:** S2; Hvis and clip summaries with confidence.
- **Missing:** clip extraction keyed to incident time, VLM adapter
  (Qwen2.5-VL primary per I-1; **frozen**, no gradients), transparent stub mode
  for machines without GPU, `sync_provenance` propagation (I-8).
- **Complexity:** Large + Research/Prototype (7B VLM inference on local
  hardware is the main uncertainty; GPU report in
  `docs/refactor_ecosystem/inventory/gpu_environment_report.md` should be
  re-verified at build time).
- **Test strategy:** stub-mode determinism tests; schema tests for `VideoClip`;
  optional integration test behind a marker (like existing `ffmpeg` marker).
- **Phase:** 7. **DoD:** every incident's clip gets a summary (real or
  explicitly stubbed), with time span + evidence ID + sync_provenance.

## DB-6 Temporal grounding producer

- **Why:** S5 is the heart of "temporally grounded"; `AlignedTuple` has no producer.
- **Missing:** module (suggest `src/temporal/`) that normalizes all three
  modalities to incident-relative time, resolves the window-convention conflict
  (±8s ETL vs 12s contract sub-windows vs -12..0 diagram — needs a
  decision-log entry, I-12), emits validated `AlignedTuple`s, and flags
  chronology violations.
- **Complexity:** Medium-Large. **Risk:** silent misalignment; mitigate with
  property tests + ledger cross-checks.
- **Phase:** 8. **DoD:** aligned tuples for all val incidents; 100% evidence_id
  resolvability (gate G2).

## DB-7 Fusion + evidence selection head

- **Why:** S6/S7; produce the evidence bundle for the decoder.
- **Missing:** projection of Hvib/Hvis/Htext into a joint space; v1
  deterministic cross-modal correlation baseline; scoring + top-K selection
  with confidences.
- **Complexity:** Large (+R/P if trainable cross-attention attempted; defer
  trainable fusion until v1 gates green).
- **Phase:** 9–10. **DoD:** ranked, traceable evidence bundle per incident.

## DB-8 Constrained decoder + prompt pipeline

- **Why:** S8; I-9 requires GBNF grammar compiled from the ExplanationOutput
  JSON Schema; I-2 requires per-claim evidence IDs.
- **Missing:** LLM provider abstraction (local llama.cpp-style GBNF path +
  fixture/mock provider for tests), prompt template from evidence bundle,
  grammar compiler, B1 free-text baseline.
- **Complexity:** Large + R/P. **Risk:** local model quality/latency; mitigate
  with mock provider so the pipeline is testable end-to-end without weights.
- **Phase:** 11. **DoD:** schema-valid `ExplanationOutput` for val incidents;
  schema_valid_rate 1.0 gate (G1).

## DB-9 Eval integration + faithfulness audit over real outputs

- **Why:** S9; metrics currently only see fixtures. **Constitution I-6:** any
  change to `src/eval/` requires a decision-log entry + meta-test re-run +
  re-scoring prior runs — plan eval extensions as additive modules where possible.
- **Missing:** adapter feeding real pipeline outputs into `compute_metrics`,
  real AUROC (needs negatives), real ECE, judge study, audit report writer,
  gates G3/G7–G11.
- **Phase:** 12. **DoD:** faithfulness report on val split from a real run,
  run record appended, no gate regression (I-10).

## DB-10 End-to-end demo + hardening

- **Why:** S10; user-testable single command + UI "Explain this incident".
- **Phase:** 13. **DoD:** `incident → explanation + audit` runs one-command;
  Streamlit page renders the chain with clickable evidence.

## Cross-cutting prerequisite: curated gold mini-set

Every learned/evaluated component above needs a small **human-curated** gold
set (sub-cause labels + true evidence spans) on the **val** split (I-4: test
stays quarantined). Recommend 20–40 incidents curated during Phases 3–6.
This is labeling work, not code, and is the single biggest scientific risk.
