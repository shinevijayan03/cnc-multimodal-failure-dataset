# Phase 6 — Validation Report (2026-07-03)

## 1. Process hygiene

All running app/dev processes stopped before coding (tasks `bg7v8b51d` +
stale port-8501 holders); verified no stray python processes.

## 2. Tests

| Suite | Result |
|---|---|
| `tests/unit/test_graph_retriever_grounding.py` (9) | graph resolve/round-trip/refusal; sensor-summary text; **topic-boost reranking**; tuple contract + chronology + I-8 caveat + evidence sets; unresolvable-evidence rejection; UI helper consumption | all pass |
| `tests/integration/test_e2e_tgfx.py` (4) | **end-to-end chain on a synthetic workspace**: ETL → assembly → D10 sub-windows → Phase 3 features → vector index → graph → grounding → UI helpers; artifact cross-consistency; grounded UI events; **broken-graph refusal (delete a node → grounding raises, I-2)** | all pass |
| Full suite | **202 passed, 1 skipped** (was 190; +12; zero broken) |
| Lint | ruff clean (2 unused imports auto-fixed during the loop) |

V&V loops: L6.1 unit-fixture gap (graph missing second window — the I-2 guard
caught it, fixture fixed); L6.2 E2E workspace used ±3/±2 s windows → zero
12 s sub-windows (correct D10 short-span behavior) → E2E fixture switched to
±8 s windows; L6.3 ruff unused imports → `--fix`.

## 3. Real-corpus results (run record `grounding_v1_…` appended)

| Metric | Value |
|---|---|
| Evidence graph | **6,063 nodes / 17,949 edges** (1,702 incidents, 3,399 windows, 934 chunks, 20 videos, 5 docs, 3 failure families) |
| Aligned tuples | **3,399** (every carved sub-window) |
| Incidents grounded | **1,702 / 1,702** |
| Evidence IDs emitted | **13,596** |
| **Evidence resolution rate (gate G2)** | **1.0** (unresolvables raise by construction; verified by the broken-graph E2E test) |
| Chronology violations | **0** |
| Sample corpus | 33-node graph, 9 tuples, resolution 1.0 (hashing fallback) |

## 4. UI verification

AppTest render tests pass against the new UI (grounded path included); app
launched on :8501, healthz 200. Grounded SOP bars, grounded sensor
chronology, and the tuples panel render from `aligned_tuples.parquet`.

## 5. Constitution checklist

I-2 enforced mechanically (resolve-or-raise + E2E refusal test) · I-6
untouched (`src/eval/` unchanged; run-record helpers imported only) · I-7
every number above traces to a command or run record · I-8 caveat embedded in
every clip_summary and the run-record notes · I-10 `evaluate --tier mvp`
inputs unchanged · I-4 grounding consumes feature/hvib tables (hvib is
train/val-only by construction).

## Verdict

Phase 6 Definition of Done + the user's integration directives: **all met.**
