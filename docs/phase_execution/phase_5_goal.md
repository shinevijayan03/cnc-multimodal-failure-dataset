# Phase 5 — Goal

**Title:** SOP embeddings + vector store (deep-build DB-3).

1. Embedding interface with **BGE-base-en-v1.5** (768-d, the exact model/dim
   the `SOPChunk` contract declares) running on the local GPU (D11), plus a
   clearly named deterministic hashing fallback for tests and the model-less
   sample smoke path.
2. Local **vector store**: exact cosine over normalized vectors, persisted to
   parquet with the embedder name recorded; search refuses mismatched
   embedders (D14).
3. Rich metadata + **citation format** per chunk
   (`sop:doc_9b792f170d38§c0021`), doc-type filtering.
4. Index build + search CLIs; `SOPChunk` contract validated on a sample.

## Entry criteria (met)

- Phase 4 approved ("Approve to start Build Phase 5"); tree clean at `b983f80`.
- `text_chunks.parquet` exists (934 chunks); sentence-transformers + torch
  CUDA available (no new installs needed).

## Definition of done

- Round-trip persist/search tests green; reload recall@1 = 1.0; metadata
  filter works; mismatched-embedder search refused.
- Real-corpus index built with BGE **on the GPU**; domain queries return
  topically correct chunks; sample-corpus index built with the fallback.
- Full suite green; ruff clean; D14 recorded; docs + user gate.
