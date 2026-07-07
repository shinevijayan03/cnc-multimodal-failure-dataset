# Phase 6 — User Review Request

```text
PHASE 6 COMPLETE — USER REVIEW REQUIRED

What changed:
- src/graph/: evidence graph (NetworkX+JSON per D7) — 6,063 nodes /
  17,949 edges over the real corpus; resolve(evidence_id) is the I-2
  resolution service (gate G2)
- src/retrieval/retriever.py: runtime retriever querying from REAL sensor
  context (RMS trend, peak interval, kurtosis) with failure-topic boosting
- src/temporal/grounding.py: REAL contract-valid AlignedTuples — 3,399
  tuples covering all 1,702 incidents, 13,596 evidence ids, resolution
  rate 1.0, 0 chronology violations; run record appended with a G2 entry
- UI: grounded SOP bars (real citations + scores over their query windows)
  replace the demo SOP row; "Grounded sensor chronology" in AI Explanation;
  "Temporal grounding" tuples panel
- Integration testing: 4 end-to-end tests exercising the full backend chain
  on a synthetic workspace, including a broken-graph refusal test

How to test (app running at http://localhost:8501):
  1. Pick any real incident → SOP row on the timeline now shows real
     citations with cosine scores (hover for provenance; no demo badge)
  2. AI Explanation tab → "Grounded sensor chronology" lists real
     per-window summaries with SW_* evidence ids
  3. Open "Temporal grounding · N aligned tuples" → full tuple table
  4. CLI: python -m src.graph.evidence_graph --resolve SW_<any-window-id>
  5. pytest -q  → 202 passed, 1 skipped

Known limitations:
  - SOP bar timing is retrieval association (real), not document
    timestamps; video sync remains constructed (I-8)
  - AI CLAIMS row stays demo until the Phase 11 decoder

GPU report (D11): grounding embedded 1,702 live BGE queries on the RTX 3060
without issue.

Please review and approve to start Build Phase 7 (video clips + frozen VLM
summaries — the quantized-7B vs 3B VLM decision is due at that gate).
```
