# Grounding and Anti-Hallucination Matrix

| Claim | Evidence Source | File/Command/Log | Confidence | Is Inference? | Verification Method | Status |
|---|---|---|---|---|---|---|
| The project is a Python codebase | Source/package files | `pyproject.toml`, `requirements.txt`, `src/*.py` | High | No | File inspection | Verified |
| The project builds a CNC multimodal failure dataset | README and module names | `README.md`, `src/etl/*`, `src/cli.py` | High | No | File inspection | Verified |
| Streamlit is the web UI framework | Dependency and imports | `requirements.txt`, `streamlit_app.py` | High | No | File inspection and running process | Verified |
| Typer is the CLI framework | Source import and CLI help | `src/cli.py`, `python -m src.cli --help` | High | No | Command output | Verified |
| Main CLI commands are sensor/text/video/assemble/all/evaluate | CLI output | `python -m src.cli --help` | High | No | Command output | Verified |
| Main web entry point is `streamlit_app.py` | Source and process command line | `streamlit_app.py`, process PID 9016 | High | No | File/process inspection | Verified |
| The app currently responds on localhost port 8501 | HTTP check | `Invoke-WebRequest http://localhost:8501` | High | No | HTTP status 200 | Verified |
| Processed artifacts exist | Pandas row-count script | `data_pipeline/data_processed/*.parquet` | High | No | Parquet read | Verified |
| Current incident count is 1702 | Pandas row-count script | `incidents.parquet` | High | No | Parquet read | Verified |
| Text chunks count is 934 | Pandas row-count script | `text_chunks.parquet` | High | No | Parquet read | Verified |
| Video index count is 20 | Pandas row-count script | `video_index.parquet` | High | No | Parquet read | Verified |
| Tests pass locally | pytest output | `pytest -q --cov=src --cov-report=term-missing` | High | No | Command output | Verified |
| Total test count is 87 | pytest collection/run | `pytest --collect-only -q`, pytest run | High | No | Command output | Verified |
| Total coverage is 82% | pytest-cov output | `pytest -q --cov=src --cov-report=term-missing` | High | No | Command output | Verified |
| Ruff lint passes | ruff output | `ruff check src tests` | High | No | Command output | Verified |
| Python compile passes | compileall output | `python -m compileall -q src streamlit_app.py` | High | No | Command output | Verified |
| ffmpeg is available | ffmpeg command | `ffmpeg -version` | High | No | Command output | Verified |
| Evaluation grade is WARN | CLI output | `python -m src.cli evaluate --tier mvp` | High | No | Command output | Verified |
| Evaluation warning source is label quality | Evaluation metrics | `pct_unknown_failure=1.0`, `dominant_class_share=1.0`, `entropy_failure=0.0` | High | No | Command output | Verified |
| No database is used | Dependency/config/source scan | requirements, config, `rg` for database terms | Medium | Yes | Negative evidence scan | Supported |
| No required env vars found | Source scan | `rg` for env/secret terms | Medium | Yes | Negative evidence scan | Supported |
| Full browser interaction is unverified | Audit scope | No Playwright/manual interaction command run | High | No | Absence of command evidence | Known unknown |
| `all --dry-run --limit 2` is not reliable as a quick smoke command | Timeout and stage isolation | CLI dry-run outputs | High | No | Command output and process check | Verified |
| Text ETL is the timeout stage | Stage isolation | `text --dry-run --limit 2` timeout | High | No | Command output | Verified |
| Text ETL timeout reproduced on revalidation | Stage isolation re-run | `text --dry-run --limit 2` timed out after 64 seconds on 2026-07-02 20:06 | High | No | Command output and orphan process stop | Verified |
| Text timeout may be caused by PDF/manual parsing or tokenization | TextETL code and manual files | `src/etl/text_etl.py`, text manual folder listing | Medium | Yes | Code-path reasoning | Inference |
| Refactor readiness is READY WITH RISKS | Audit synthesis | Runtime/tests green, dirty tree and text timeout risks | Medium | Yes | Rubric and V&V synthesis | Decision |
