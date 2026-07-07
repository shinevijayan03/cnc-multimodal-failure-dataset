# 12 — Grounding Traceability Matrix (Audit Stage)

Every major claim made in artifacts 00–13. Confidence: High/Medium/Low.
Status: Verified (direct observation) / Inference (reasoned from evidence) /
Assumption / Unknown.

| # | Claim | Evidence Source | File / Command / Output | Confidence | Inference? | Status |
|---|---|---|---|---|---|---|
| 1 | Working tree clean at audit start | command | `git status --porcelain` → empty | High | No | Verified |
| 2 | HEAD = 547f2c1 on codex/complete-pending-phases | command | `git rev-parse HEAD`, `git branch --show-current` | High | No | Verified |
| 3 | Test suite green | command | `pytest -q` → 106 passed, 1 skipped, 8.17s | High | No | Verified |
| 4 | Skipped test is opt-in browser smoke | file | `pyproject.toml` markers; `tests/ui/test_streamlit_browser_smoke.py` | High | No | Verified |
| 5 | Dataset grades PASS at mvp tier, 1702 incidents | command | `python -m src.cli evaluate --tier mvp` stdout | High | No | Verified |
| 6 | Split = train 1192 / val 255 / test 170 / human_eval 85 | command | same stdout `split_dist` | High | No | Verified |
| 7 | Streamlit app starts and serves | command | headless start + `GET /healthz` → 200 | High | No | Verified |
| 8 | Sensor/text ETL stages execute | command | `src.cli sensor/text --dry-run` outputs | High | No | Verified |
| 9 | ffmpeg available; video stage runnable | command | `Get-Command ffmpeg` → 8.1.1 path | High | No | Verified |
| 10 | Lint + compile clean | command | `ruff check` "All checks passed!"; `compileall` OK | High | No | Verified |
| 11 | TGFX fixture eval harness runs | command | `python -m src.eval.run --fixtures oracle --no-write` metrics JSON | High | No | Verified |
| 12 | No encoder/VLM/retriever/graph/fusion/decoder code exists | file inventory | `find` output: no `src/encoder|vision|retrieval|graph|temporal|fusion|explain`; `docs/_sdd/tasks.md` T-10+ "Not started" | High | No | Verified |
| 13 | No embedding code despite SOPChunk declaring BGE model | file | `contracts/core.py:90-91`; no embedding imports repo-wide | High | No | Verified |
| 14 | AlignedTuple/ExplanationOutput have no producers | file | `contracts/` definitions; only `src/eval/fixtures.py` constructs ExplanationOutput (hand-authored) | High | No | Verified |
| 15 | Labels are weak deterministic scaffolding | file | README demo-build note; `docs/_data/manifest.json` `label_status`; `assemble_incidents.LabelDeriver.weak_*` | High | No | Verified |
| 16 | Video-incident sync is constructed, not measured | file | `src/tgfx/dataset.py:82` hardcodes `"sync_provenance": "constructed"`; `alignment_ledger.jsonl` | High | No | Verified |
| 17 | AUROC and ECE in TGFX metrics are placeholders | file | `src/eval/metrics.py:148-149, 199-201` (explicit comments) | High | No | Verified |
| 18 | LLM judge is placeholder | file | `src/eval/verify_llm.py` docstring "deferred … fixture behavior" | High | No | Verified |
| 19 | RMS math duplicated (I-3 tension) | file | `src/features/vibration.py:14` vs `src/etl/sensor_etl.py:246` `_sliding_rms` | High | No | Verified |
| 20 | Retrieval is keyword-topic, not vector/BM25 at runtime | file | `assemble_incidents.TextRetriever`; config `method: keyword_bm25`; `rank-bm25` optional dep unused in code path | Medium | Partially (BM25 unused judged from imports) | Verified |
| 21 | Regime labels never derived (all unknown) | command | evaluate stdout `regime_dist: {'unknown': 1702}` | High | No | Verified |
| 22 | Fresh clone cannot run demo (data gitignored) | file + reasoning | `.gitignore` data rules; ETL discovers files only under data_raw | Medium | Yes | Inference |
| 23 | CI green on this branch | — | not executed | — | — | Unknown |
| 24 | Test coverage is 80% | README (dated 2026-07-02) | README validation snapshot; not re-measured | Medium | No | README-reported, not audit-verified |
| 25 | 7B VLM inference feasible on this machine | — | GPU report exists (`docs/refactor_ecosystem/inventory/gpu_environment_report.md`) but not re-verified | Low | — | Unknown |
| 26 | Window-convention conflict (±8s vs 12s vs -12..0) | file | `config windowing`, `contracts/core.py:54`, user diagram 1 | High | No | Verified |
| 27 | data/splits/test.jsonl contents | — | **not read (constitution I-4 quarantine)** | — | — | Deliberately Unknown |
| 28 | Constitution gates G3, G7–G11 not implemented | file | `docs/_eval/gates.yaml` (`implemented: fixture_only` / `false`) | High | No | Verified |
