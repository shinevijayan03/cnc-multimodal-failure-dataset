# Phase 5 — User Review Request

(Design rationale: D14 in `docs/_sdd/decisions.md`; V&V loop table:
validation report §6; rubric: implementation log — consolidated this phase.)

```text
PHASE 5 COMPLETE — USER REVIEW REQUIRED

What changed:
- src/retrieval/: BGE-base-en-v1.5 embeddings on the GPU (contract-exact
  768-d), deterministic hashing fallback (clearly named), exact-cosine
  vector store persisted to parquet with embedder-name guard, citations
  (sop:doc_x§c0021), index-build + search CLIs
- config retrieval section + vector_store paths; D14 decision; 11 new tests

How to test:
  python -m src.retrieval.search --query "bearing vibration threshold" --k 5
  python -m src.retrieval.search --query "coolant flow" --doc-type maintenance --k 3
  pytest -q

Expected result:
  - ranked hits with scores ~0.6+, citations, topic tags, text previews;
    doc-type filter restricts results
  - pytest: 185 passed, 1 skipped

Known limitations:
  - Match scores are cosine similarities, not calibrated relevance
    probabilities (the SOP-card match-% in the UI stays demo-badged until
    the Phase 6 retriever wires real scores in)
  - Retrieval is chunk-level; incident-context query construction and the
    evidence graph arrive in Phase 6

GPU report (D11): BGE embedding of the full 934-chunk corpus took 6.24 s on
the RTX 3060 — no issues found this phase.

Please review and approve to start Build Phase 6 (evidence graph +
runtime retriever).
```
