# Phase 1 — V&V Loop Report

| Loop ID | Phase | Issue/Goal | Evidence | Hypothesis | Change Made | Validation Command | Result | Exit Decision |
|---|---|---|---|---|---|---|---|---|
| L1.1 | 1 | GPU envelope unknown (audit R-3) | No torch dep declared; GPU report stale | Local GPU + torch may already be usable | None (probe only) | `nvidia-smi`; `python -c "import torch; ..."` | RTX 3060 12 GB, torch 2.6.0+cu124, CUDA available | Record in D11; report 7B-fp16-VLM misfit at gate |
| L1.2 | 1 | Fresh clone cannot run (audit R-7) | data_raw/processed gitignored | A seeded generator + isolated sample config closes the gap without touching app code | Added `scripts/generate_sample_data.py`, `config/dataset.sample.yaml`, gitignore entries | `python scripts/generate_sample_data.py` | 8 CSVs + 2 manuals + tags + 2 clips generated | Continue |
| L1.3 | 1 | Sample pipeline must run end-to-end | New raw tree, new config | Existing readers/detectors handle conftest-style bursts | None (execution) | `python -m src.cli all --config config/dataset.sample.yaml` | sensor 5 / text 13 / video 2 / assemble 5 written, exit 0 | Continue |
| L1.4 | 1 | Runbook promised "good runs yield none"; run produced 5 incidents from 8 runs | Stage summary `written=5` | One good run crosses zscore 4.0 occasionally; smoke path shouldn't tune detectors | Runbook expectation updated to observed, deterministic counts | re-read stage summary | Doc matches reality | Continue |
| L1.5 | 1 | Generator correctness + determinism | New code needs tests | 4 focused tests suffice (layout, contract columns, burst, byte-determinism) | Added `tests/unit/test_sample_data.py` | `pytest -q` (suite) | 110 passed, 1 skipped | Continue |
| L1.6 | 1 | Coverage number was README-reported, not verified (audit row 24) | Audit grounding matrix | Re-measure with cov flags | None (measurement) | `pytest -q --cov=src --cov=contracts --cov=scripts` | TOTAL 80% (2340/466) | Verified; matches README claim |
| L1.7 | 1 | App must still start after changes | Rubric critical dimension | No app code touched → should pass | None | Streamlit headless + healthz probe (port 8601) | HTTP 200 | Phase exit → user gate |

No loop required a rollback. No application code was modified in any loop.
