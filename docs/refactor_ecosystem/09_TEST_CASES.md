# Test Cases

## Purpose

Provide a Stage A test case register covering current tests and proposed Stage B tests for Streamlit, GPU, diagnostics, and documentation refresh.

## Current Verified Test Families

| Family | Existing IDs | Status |
|---|---|---|
| Config | UT-CFG-01..06 | Implemented and passing |
| Schemas | UT-SCH-01..05 plus serialization | Implemented and passing |
| IO and IDs | UT-IO-01..06, UT-ID-01..02 | Implemented and passing |
| Sensor | UT-SENS-01..15, IT-SENS-01..04 | Implemented and passing |
| Text | UT-TEXT-01..08, IT-TEXT-01 | Implemented and passing |
| Video | UT-VID-01..07 | Implemented and passing |
| Assembly | UT-ASM-01..12, IT-ASM-01..04 | Implemented and passing |
| CLI/Evaluation | UT-CLI-01..03, IT-EVAL-01..02 | Implemented and passing |
| E2E | E2E-01..02 | Implemented and passing |

## Stage B Proposed Test Cases

| ID | Area | Title | Preconditions | Steps | Expected Result |
|---|---|---|---|---|---|
| UT-DIAG-01 | Diagnostics | ffmpeg missing detection | Mock PATH without ffmpeg | Run diagnostics | Reports ffmpeg unavailable with install hint |
| UT-DIAG-02 | Diagnostics | optional dependency report | Mock import results | Run diagnostics | Reports missing/present optional deps |
| UT-DIAG-03 | Diagnostics | raw data readiness | Temp repo with/without data roots | Run readiness check | Shows expected missing/present folders |
| UT-RUN-01 | Runner | single-stage routing | Mock stage classes | Run `sensor` selection | Calls `SensorETL.run` with limit/dry-run |
| UT-RUN-02 | Runner | all-stage order | Mock stage classes | Run all | Calls sensor, text, video, assemble in order |
| UT-RUN-03 | Runner | assembly failure surfaced | Missing sensor index | Run assemble | Returns actionable error |
| UT-UI-01 | Streamlit | app import smoke | UI implemented | Import UI module | No ETL runs during import |
| UT-UI-02 | Streamlit | config summary model | Valid config | Build UI config summary | Path table and key settings returned |
| UT-UI-03 | Streamlit | output discovery | Temp output files | Discover artifacts | Reports present/missing outputs |
| IT-UI-01 | Streamlit | local UI smoke | UI implemented | Launch app manually or via test harness | Page renders core controls |
| UT-GPU-01 | GPU | prefer CPU | Device utility implemented | `prefer_gpu=False` | Returns CPU |
| UT-GPU-02 | GPU | CUDA selected | Mock torch CUDA true | `prefer_gpu=True` | Returns CUDA metadata |
| UT-GPU-03 | GPU | CUDA fallback | Mock torch CUDA false | `prefer_gpu=True` | Returns CPU with fallback reason |
| UT-GPU-04 | GPU | torch missing | Mock ImportError | `prefer_gpu=True` | Returns CPU without crash |
| IT-GPU-01 | GPU | local PyTorch GPU check | RTX 3060 machine | Run device utility | Detects GPU if available |
| UT-MD-01 | Docs | README commands current | README updated | Parse command snippets manually or with docs test | Commands match project |
| UT-CFG-07 | Config | retrieval method validation | Invalid method | Load config | ConfigError names method |
| UT-RET-01 | Retrieval | BM25 or renamed topic overlap | Strategy implemented | Retrieve chunks | Method matches documented behavior |

## Acceptance Test Cases

| ID | Title | Steps | Expected Result |
|---|---|---|---|
| ACC-01 | Default docs review | Open `docs/refactor_ecosystem/00_EXECUTION_SUMMARY.md` and checklist | Reviewer can decide Stage B approval |
| ACC-02 | CLI build with staged raw data | Stage small raw data and run `python -m src.cli all` | `incidents.parquet` produced |
| ACC-03 | Evaluation report | Run `python -m src.cli evaluate --tier mvp` | `eval_report.json` and `.md` produced |
| ACC-04 | Streamlit launch | Run `streamlit run streamlit_app.py` | UI loads and shows diagnostics |
| ACC-05 | CPU fallback | Disable GPU preference and run approved GPU feature | Completes on CPU |
| ACC-06 | GPU path | Enable GPU preference for approved feature | Logs CUDA device or CPU fallback |

## Current Evidence

- `python -m pytest -q`: 76 passed.
- `python -m pytest --collect-only -q`: 76 tests collected.
- `python -m compileall -q src tests`: passed.
- `python -m ruff check src tests`: 8 advisory findings.
