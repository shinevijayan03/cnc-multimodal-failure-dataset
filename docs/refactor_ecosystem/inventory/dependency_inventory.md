# Dependency Inventory

## Purpose

Record the dependency, package, runtime, CI, and external tool state discovered during Stage A.

## Runtime Stack

| Area | Current Finding |
|---|---|
| Language | Python |
| Python version used locally | Python 3.12.7 |
| Supported Python declared by project | >=3.10 |
| Package metadata | `pyproject.toml` |
| Install file | `requirements.txt` |
| CLI framework | Typer |
| Test framework | pytest |
| Data stack | pandas, numpy, scipy, pyarrow |
| Validation stack | pydantic v2, pyyaml |
| Video external tool | ffmpeg/ffprobe expected on PATH, currently missing locally |
| Frontend/UI | No project UI module; Streamlit is installed in the environment but not declared or used by this repo |
| GPU/ML declared deps | None declared in `pyproject.toml` or `requirements.txt` |

## Project Dependencies

Current required dependencies from `pyproject.toml` and `requirements.txt`:

| Package | Role |
|---|---|
| pydantic>=2.5 | Typed config and row schemas |
| pyyaml>=6.0 | YAML config parsing |
| pandas>=2.0 | DataFrame ETL and Parquet IO |
| pyarrow>=12.0 | Parquet backend |
| numpy>=1.24 | Numeric arrays, signal/window logic |
| scipy>=1.10 | Numeric/scientific dependency, currently listed but not heavily used in core source |
| typer>=0.9 | CLI commands |

Optional dependency groups in `pyproject.toml`:

| Group | Packages | Current Use |
|---|---|---|
| text | tiktoken, pypdf, python-docx | token counting and PDF/DOCX text extraction |
| retrieval | rank-bm25 | planned BM25 retrieval, current code uses topic-tag overlap fallback |
| eval | matplotlib | evaluation reporting/plotting support |
| dev | pytest, pytest-cov | testing and coverage |

Local import availability check:

| Package | Local Result |
|---|---|
| pydantic | installed |
| yaml | installed |
| pandas | installed |
| pyarrow | installed |
| numpy | installed |
| scipy | installed |
| typer | installed |
| tiktoken | missing |
| pypdf | missing |
| docx | installed |
| rank_bm25 | missing |
| matplotlib | installed |
| pytest | installed |
| streamlit | installed, not project-declared |
| h5py | installed |

## External Tools

| Tool | Local Result | Impact |
|---|---|---|
| ffmpeg | missing from PATH | Video stage skips cleanly; real video normalization unavailable until installed |
| ffprobe | inferred missing because ffmpeg is missing | Same as ffmpeg |
| nvidia-smi | available | GPU hardware is visible |
| GitHub Actions | `.github/workflows/ci.yml` present | CI tests Python 3.10, 3.11, 3.12, 3.13 |

## Build and Run Commands

| Command | Purpose | Stage A Result |
|---|---|---|
| `python -m pip install -r requirements.txt` | Install dependencies | Documented, not rerun in Stage A |
| `python -m src.cli --help` | Inspect CLI | Succeeded |
| `python -m src.cli all --config config/dataset.yaml --dry-run --limit 1` | Local smoke dry-run | Fails at assembly because no raw sensor index exists; upstream stages report no staged raw data |
| `python -m src.cli evaluate --config config/dataset.yaml --tier mvp` | Evaluation | Fails because `data_processed/incidents.parquet` does not exist |
| `python -m pytest -q` | Test suite | 76 passed |
| `python -m compileall -q src tests` | Syntax/import compilation smoke | Succeeded |
| `python -m ruff check src tests` | Advisory lint | 8 unused import/variable issues |

## Dependency Risks

| ID | Risk | Impact | Recommended Action |
|---|---|---|---|
| DEP-01 | `ffmpeg` is absent locally | Real video ETL cannot normalize clips | Install ffmpeg or document skip behavior prominently |
| DEP-02 | `tiktoken` and `pypdf` are listed but missing locally | Text ETL falls back or skips PDF extraction | Install full requirements before thesis-scale text build |
| DEP-03 | `rank_bm25` is missing and not currently used by retrieval code | Config says `keyword_bm25`, but implementation uses topic-overlap fallback | Either implement BM25 or rename/document current retrieval |
| DEP-04 | Streamlit installed in environment but not declared | UI plan cannot be reproduced from project dependencies | Add Streamlit in Stage B if UI is approved |
| DEP-05 | GPU libraries exist in environment but not project dependencies | GPU plan would be environment-coupled | Add optional GPU extras only if GPU work is approved |
