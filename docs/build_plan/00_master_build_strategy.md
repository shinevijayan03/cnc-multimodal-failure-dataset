# 00 — Master Build Strategy

## Objective

Evolve the existing Recipe A dataset pipeline + TGFX eval substrate (audited at
commit `547f2c1`, runtime state RUNS) into the full temporally grounded
multimodal failure-explanation system defined in
`docs/architecture_audit/04_target_architecture_interpretation.md`.

## Strategy principles

1. **Substrate-first is already done — exploit it.** Contracts, metric harness,
   run records, split manifests, and the ETL pipeline exist and are green.
   Every new component must *consume* these (produce contract instances, be
   scored by the existing harness) rather than invent parallel structures.
2. **Constitution is binding** (`CLAUDE.md`): frozen VLM (I-1), evidence-or-
   silence (I-2), one feature path (I-3), test quarantine (I-4), seeded run
   records (I-5), metric freeze process (I-6), no fabricated numbers (I-7),
   sync provenance caveats (I-8), GBNF decoding (I-9), ratchet merges (I-10),
   ≤600-line branches (I-11), BLOCKED memos over cleverness (I-12).
3. **Deterministic baseline before learned component**, at every layer:
   heuristic anomaly score before trained encoder; correlation before
   cross-attention; mock provider before real LLM; stub summaries before VLM.
   This keeps the app runnable at the end of every phase (user review gates).
4. **Two parallel tracks, serialized by default:** sensor track (Phases 2–4)
   and text/RAG track (Phases 5–6) are independent; video (7) joins at
   grounding (8). Serial execution keeps diffs reviewable (I-11); parallelize
   only if the user asks for speed.
5. **ETVX discipline per phase:** Entry criteria checked, Task executed,
   Validation (focused tests + full suite + app run), eXit only after the
   user-review gate approves. V&V loop table maintained in each phase's
   `phase_N_vnv_loop_report.md`.
6. **Anti-hallucination:** all claims in phase docs must cite file/command/log;
   PENDING(run_id) placeholders for any number not yet produced (I-7).

## Phase order (from audit roadmap `13_recommended_build_roadmap.md`)

1 Baseline hardening → 2 Windowing convention + sensor evidence IDs →
3 Patches + one-feature-path spectral features → 4 Pluggable encoder (Hvib) →
5 Embeddings + vector store → 6 Evidence graph + retriever →
7 Video clips + frozen VLM (stub-transparent) → 8 Temporal grounding producer →
9 Fusion baseline → 10 Evidence selection head → 11 Constrained decoder →
12 Eval/faithfulness integration → 13 End-to-end demo.

Cross-cutting: gold mini-set curation on val (starts Phase 3, must finish
before Phase 10 numbers are quoted).

## Module placement plan (new code)

| Capability | New module | Consumes | Produces |
|---|---|---|---|
| Patching + spectral bands | `src/features/vibration.py` (extend) + `src/features/patching.py` | waveform parquet | patch tokens, 4-band features |
| Encoder | `src/encoder/` | patches | Hvib, anomaly_score |
| Embeddings + vector store | `src/retrieval/embeddings.py`, `src/retrieval/store.py` | text_chunks.parquet | SOPChunk + search API |
| Evidence graph | `src/graph/` | ledger, indices | node/edge store, resolve(evidence_id) |
| Retriever | `src/retrieval/retriever.py` | store + graph + context | ranked SOP evidence |
| VLM adapter | `src/vision/` | video clips | VideoClip w/ clip_summary |
| Temporal grounding | `src/temporal/` | all above | AlignedTuple stream |
| Fusion + selection | `src/fusion/` | Hvib/Hvis/Htext | evidence bundle |
| Decoder | `src/explain/` | bundle | ExplanationOutput (GBNF) |
| Eval integration | `src/eval/` (additive; I-6 process) | outputs + gold | run records, audit report |

## Definition of success

See `02_definition_of_done.md`. Ultimate gate: the 20-point project DoD from
the user's brief, each point mapped to a runnable command and a run record.
