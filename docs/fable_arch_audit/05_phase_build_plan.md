# 05 — Phase Build Plan (fable_prompt phases mapped to actual repo state)

The repo already completed most of fable_prompt Phases 1–5 under its own
roadmap (commits `e53b174…05761b6`, gate-approved). Remaining work re-phased:

| fable_prompt Phase | Status vs repo | Remaining scope |
|---|---|---|
| P1 Data contracts | **DONE** (`contracts/`, D10 time utility, fixtures, tests) | — |
| P2 Sensor pipeline | **DONE except** real PatchTST (B-6) + predicted_sensor_state (B-7) | defer B-6 behind gold labels |
| P3 Video pipeline | **DONE** (frozen Qwen2.5-VL-3B + tags fallback + tests) | LLaVA comparison B-11 optional |
| P4 SOP RAG | **PARTIAL** — embeddings/store/graph/retriever done | **B-5**: upload UI, OCR hook, 5-facet tagging, upload security tests |
| P5 Grounding + fusion | grounding **DONE** (3399 real tuples, G2=1.0) | **B-2** selection head + context builder, **B-9** wiring |
| P6 Decoder LLM | **NOT IMPLEMENTED** | **B-1** full build (mock provider first, then local GGUF + GBNF per D2/I-9) |
| P7 UI refactor | **LARGELY DONE** (synchronized timelines, evidence bars, export) | **B-4**: evidence click-to-highlight, decoder panel, audit panel |
| P8 Faithfulness audit | **PARTIAL** (fixture harness) | **B-3** real-output eval + report (I-6 process) |
| P9 Hardening | pending | **B-12** final compliance/diff/security review |

## Execution order proposed (one approval gate each)

1. **Build-A (≈ fable P5 residual):** B-2 + B-9 — fusion/evidence-selection
   head + context builder; reground; UI bundle view. Tests: selection ranking,
   traceability, context shape.
2. **Build-B (fable P6):** B-1 decoder — mock provider first (schema-valid
   output end-to-end), then local Qwen2.5-7B-Instruct Q4_K_M GGUF via
   llama.cpp with JSON-schema→GBNF (D2, I-9); guardrails emit
   `unsupported_claims`. Tests: prompt contract, JSON validity, citation
   resolution, unsupported-claim detection.
3. **Build-C (fable P7 residual):** B-4 UI — decoder explanation panel, audit
   panel, clickable evidence markers (Altair `on_select`) with source
   highlighting. AppTest + interaction tests.
4. **Build-D (fable P8):** B-3 faithfulness audit over real decoder outputs;
   run records; report UI. I-6: decision-log entry + meta-test rerun +
   re-score priors.
5. **Build-E (fable P4 residual):** B-5 SOP upload UI + OCR + 5-facet tagging
   (+ security_reviewer pass — new upload path).
6. **Build-F (fable P9):** B-12 hardening + final compliance matrices.

Parallel human workstream from day 1: **B-10 gold mini-set** (unblocks honest
decoder/audit/encoder metrics; constitution I-7 keeps numbers caveated until
then).

Constraints honored: I-11 ≤ ~600 lines per branch (each Build splits if
needed); every phase ends with tests + app run + URL + user approval gate.
