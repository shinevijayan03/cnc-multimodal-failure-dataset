# Phase 5 — Validation Report (2026-07-03)

## 1. Focused tests

`pytest tests/unit/test_retrieval.py -q` → **11 passed in 0.71s**

Covered: hashing embedder determinism/normalization/shape + similarity
reflects token overlap; unknown-kind rejection; store cosine ranking;
metadata (doc_type) filtering; **round-trip persistence with reload
recall@1 = 1.0**; mismatched-embedder refusal; duplicate-id and bad-shape
rejection; citation format; metadata builder; `SOPChunk` contract sample
validation.

## 2. Full suite + lint

- `pytest -q` → **185 passed, 1 skipped in 67.69s** (was 174; +11; zero broken)
- `ruff check src tests contracts scripts streamlit_app.py` → All checks passed!

## 3. Real-corpus index build (GPU, per D11)

`python -m src.retrieval.build_index --config config/dataset.yaml` →

```json
{"chunks": 934, "dim": 768, "embedder": "BAAI/bge-base-en-v1.5",
 "contract_validated": 5, "embed_seconds": 6.24,
 "out": ".../data_processed/vector_store.parquet"}
```

## 4. Retrieval quality spot-checks (real BGE index)

| Query | Top hits (topics) | Sensible? |
|---|---|---|
| "bearing vibration threshold exceeded" | maintenance chunks tagged vibration,spindle (0.634, 0.626) about spindle vibration diagnosis | ✅ |
| "coolant flow inspection and lubricant starvation" | coolant,spindle chunks about coolant condition/levels and through-spindle coolant alarms (0.669, 0.657, 0.643) | ✅ |
| "tool wear flank inspection" `--doc-type sop` | SOP-only hits led by tool-offset/wear and machining-quality chunks | ✅ (filter verified) |

## 5. Sample smoke path

`build_index --config config/dataset.sample.yaml` → 13 chunks, embedder
recorded as `hashing_fallback` (0.11 s, no model download) — the store can
never masquerade as BGE.

## 6. V&V loop

| Loop | Issue | Fix | Validation |
|---|---|---|---|
| L5.1 | `UnicodeEncodeError` printing PDF bullet chars (\x95) on the cp1252 Windows console during `search` output | encoding-safe `_println` (ascii-replace fallback) | re-ran the failing query — clean output |

## 7. Ratchet / records

- `src/eval/` untouched (I-6); no KPI gate affected; `evaluate` inputs unchanged.
- No model was trained and no eval metric produced → no runs.jsonl record
  required; index-build numbers trace to the commands above (I-7).

## Verdict

Phase 5 Definition of Done: **all items met.**
