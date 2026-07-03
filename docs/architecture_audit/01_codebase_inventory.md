# 01 — Codebase Inventory

Snapshot at commit `547f2c1` on branch `codex/complete-pending-phases` (clean tree).

## Technology stack (verified from files)

| Aspect | Value | Evidence |
|---|---|---|
| Language | Python (>= 3.10; runtime is 3.12.7) | `pyproject.toml` `requires-python`; `python --version` |
| Package manager | pip / setuptools | `pyproject.toml` `[build-system]`, `requirements.txt` |
| Core deps | pydantic v2, pyyaml, pandas, pyarrow, numpy, scipy, typer, streamlit | `pyproject.toml` `[project.dependencies]` |
| Optional deps | tiktoken/pypdf/python-docx (text), rank-bm25 (retrieval), matplotlib (eval), pytest/pytest-cov (dev) | `pyproject.toml` `[project.optional-dependencies]` |
| CLI framework | Typer (`recipe-a` console script; `python -m src.cli`) | `pyproject.toml` `[project.scripts]`, `src/cli.py` |
| UI | Streamlit (`streamlit_app.py`) | file present; smoke-tested OK |
| Test framework | pytest (markers: `ffmpeg`, `browser`) | `pyproject.toml` `[tool.pytest.ini_options]` |
| Lint | ruff (line-length 100, py310) | `pyproject.toml` `[tool.ruff]` |
| CI | GitHub Actions | `.github/workflows/ci.yml` |
| External binary | ffmpeg/ffprobe (video stage; skips cleanly if absent) | `src/etl/video_etl.py`, README |

## Source layout

```text
config/dataset.yaml            # single source of truth for pipeline knobs
contracts/                     # TGFX pydantic contracts (core.py, explanation.py)
src/
├── cli.py                     # Typer CLI: sensor|text|video|assemble|all|evaluate
├── evaluate.py                # dataset-quality metrics + PASS/WARN/FAIL tiers
├── common/                    # config loader, errors, ids, io_utils, logging, schemas
├── etl/
│   ├── sensor_etl.py          # readers, Normalizer, FsEstimator, EventDetector,
│   │                          #   WindowCarver, EvidenceSpanExtractor
│   ├── text_etl.py            # DocReader (md/txt/docx/pdf), Chunker, TopicTagger
│   ├── video_etl.py           # FfprobeReader, FfmpegNormalizer, TagMerger
│   └── assemble_incidents.py  # LabelDeriver, VideoMatcher, TextRetriever,
│                              #   SplitAssigner, IncidentAssembler
├── eval/                      # TGFX eval harness: metrics, fixtures, run records,
│                              #   verify_sensor (rule-based), verify_llm (placeholder)
├── features/vibration.py      # single feature path: rms, variance, kurtosis, rose
├── tgfx/dataset.py            # manifest + alignment ledger + split scaffolding
└── ui/incident_explorer.py    # data-loading helpers for the Streamlit explorer
streamlit_app.py               # incident explorer entry point
scripts/build_dataset.py       # CLI wrapper for src.tgfx.dataset
tests/                         # unit, integration, contracts, eval_meta, ui (107 tests)
data/splits/                   # train/val/test/human_eval JSONL id manifests
data_pipeline/data_processed/  # built artifacts: incidents.parquet, sensor_windows.parquet,
                               #   text_chunks.parquet, video_index.parquet, eval_report.{json,md}
docs/                          # design docs + prior generated doc sets + _sdd/_eval/_data
```

## Entry points

| Entry point | Purpose | Verified |
|---|---|---|
| `python -m src.cli <stage>` | ETL pipeline stages + dataset evaluation | dry-runs executed OK |
| `python -m src.eval.run --fixtures oracle` | TGFX fixture eval, appends `docs/_eval/runs.jsonl` | executed with `--no-write` OK |
| `python scripts/build_dataset.py` | TGFX manifest/ledger/splits | covered by unit tests |
| `streamlit run streamlit_app.py` | Incident explorer UI | headless smoke OK (healthz 200) |
| `pytest -q` | Test suite | 106 passed, 1 skipped |

## Data folders

- `data_pipeline/data_raw/` — gitignored; user-staged raw inputs (sensor CSVs, videos + `video_tags.csv`, PDF/MD manuals). Present locally (text dry-run discovered 5 docs; sensor dry-run discovered CSVs).
- `data_pipeline/data_processed/` — gitignored except committed demo parquet outputs exist locally; `incidents.parquet` has 1702 rows (from `evaluate` output).
- `data/splits/` — committed ID/provenance manifests. **`test.jsonl` is quarantined** (constitution I-4) and was not read.

## Model files

None. No trained model weights, no encoder checkpoints, no VLM/LLM integration
code exist anywhere in the repository (verified by inventory; no `src/encoder/`,
`src/vision/`, `src/retrieval/`, `src/graph/`, `src/fusion/`, `src/explain/`).
This matches `docs/_sdd/tasks.md` (T-10 onward "Not started").
