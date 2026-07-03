# 02 — Definition of Done

## Project-level DoD (20 points, from the user brief)

Each point must be demonstrable by a command and, where a number is produced,
a `docs/_eval/runs.jsonl` record (I-5/I-7). Status column starts from the
audit findings and is updated at each phase gate.

| # | Criterion | Verification command (target) | Status at audit (547f2c1) |
|---|---|---|---|
| 1 | Raw vibration data ingested | `python -m src.cli sensor` | ✅ done (verified) |
| 2 | Incident windows selected | same + window tests | ✅ done; convention decision pending (R-4) |
| 3 | Sensor patches created | Phase-3 unit tests | ❌ missing |
| 4 | Encoder produces embeddings / validated summaries | Phase-4 run record | ❌ missing |
| 5 | Degradation signatures detected | anomaly-score eval vs baseline | ❌ heuristic spans only |
| 6 | Video clips ingested and summarized | Phase-7 pipeline output | ◐ ingested ✅ / summarized ❌ |
| 7 | SOP/manuals ingested and chunked | `python -m src.cli text` | ✅ done (verified) |
| 8 | Vector DB retrieval works | Phase-5 search test | ❌ missing |
| 9 | Evidence graph works | Phase-6 resolution test | ❌ missing |
| 10 | Temporal grounding creates aligned tuples | Phase-8 producer output | ❌ contract only |
| 11 | Multimodal fusion works | Phase-9 bundle test | ❌ missing |
| 12 | Evidence selection works | Phase-10 ranking test | ❌ missing |
| 13 | Decoder LLM generates structured explanations | Phase-11, schema_valid_rate 1.0 | ❌ missing |
| 14 | Every generated claim is evidence-linked | contract + G2 gate | ◐ enforced in schema/metrics; no generator |
| 15 | Chronology validated | contract validator + wrong_time metric | ✅ mechanism exists (needs real outputs) |
| 16 | Faithfulness audit runs | Phase-12 audit report | ◐ fixture harness only |
| 17 | End-to-end demo runs | Phase-13 one-command | ❌ missing |
| 18 | Tests cover core modules | `pytest -q` | ✅ for existing scope (106 green) |
| 19 | App runs successfully | Streamlit + CLI smoke | ✅ verified (RUNS) |
| 20 | User reviewed and accepted each phase | signed `phase_N_feedback_incorporation.md` | ⏳ gates begin at Phase 1 |

## Phase-level DoD template

A phase is done only when ALL hold:

1. Entry criteria were met and recorded.
2. All phase deliverables implemented; diff per branch ≤ ~600 lines (I-11).
3. Focused tests added and passing; **full** `pytest -q` green.
4. `ruff check` clean; app starts (Streamlit healthz or CLI smoke).
5. Any metric produced has a run record with git_sha/config_hash/seed/
   dataset_manifest_hash (I-5); no val KPI gate regressed (I-10).
6. Phase docs written: goal, design, implementation log, validation report,
   V&V loop table, rubric score (critical dimensions ≥ 3).
7. `PHASE N COMPLETE — USER REVIEW REQUIRED` posted with exact test commands.
8. User feedback received and incorporated (`phase_N_feedback_incorporation.md`).
9. Anything touching `src/eval/` followed the I-6 freeze process.
10. Test split never read outside `scripts/eval_test.py` (I-4).
