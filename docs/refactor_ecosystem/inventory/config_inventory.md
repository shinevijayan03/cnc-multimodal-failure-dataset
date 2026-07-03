# Configuration Inventory

## Purpose

Inventory the configuration files and runtime knobs that control the pipeline.

## Configuration Files

| File | Role | Notes |
|---|---|---|
| `config/dataset.yaml` | Main runtime configuration | Loaded by `src.common.config.load_config()` |
| `pyproject.toml` | Package metadata, dependencies, pytest and ruff config | Defines package `recipe-a-pipeline` and script `recipe-a = src.cli:app` |
| `requirements.txt` | pip install list | Includes runtime, optional text/retrieval/eval, and dev/test dependencies |
| `.github/workflows/ci.yml` | CI config | Runs tests on Python 3.10-3.13; lint advisory |
| `.gitignore` | Data/cache exclusion policy | Excludes raw data, processed data, logs, venvs, caches |

## `config/dataset.yaml` Sections

| Section | Current Responsibility |
|---|---|
| `version` | Config schema version, currently `0.1.0` |
| `random_seed` | Global deterministic seed |
| `paths` | Raw input roots, processed output paths, logs |
| `sensor` | Dataset readers, canonical channels, fs estimation, event detection, windowing, evidence spans |
| `video` | ffmpeg normalization settings, tag vocabularies, tagging CSV |
| `text` | Input formats, chunking parameters, doc types, topic keywords |
| `assemble` | Video matching, text retrieval, labels, split policy |
| `runtime` | Log level/format, fail-fast behavior, workers, dry-run default |

## Current Config Drift

| Finding | Evidence | Impact |
|---|---|---|
| Header still says "Phase-1 STUB" and "not yet consumed by code" | `config/dataset.yaml` comments | Incorrect; `load_config()` validates and stages consume the config |
| `TODO(review)` comments remain | Bosch raw format, output format, tokenizer | Open design decisions should be promoted to the open-items register |
| `runtime.num_workers` exists but no stage uses parallel workers | Config and source review | Concurrency knob is currently informational |
| `sensor.output_format` allows parquet/hdf5 in comments, but implementation writes Parquet only | `sensor_etl.py` uses `write_parquet_atomic` | Either enforce/document parquet or implement HDF5 path |
| `assemble.text_retrieval.method` says `keyword_bm25`, but `TextRetriever` uses topic-overlap scoring | Config/source review | Naming may overpromise BM25 behavior |

## Path Resolution

`load_config()` sets `repo_root` from the config file location and resolves every `paths.*` field to an absolute path. This is good for runtime reliability, but docs should mention that config paths are authored as repo-relative and become absolute at load time.

## CLI-Controlled Config Overrides

Current CLI accepts:

| Option | Meaning |
|---|---|
| `--config`, `-c` | Choose a config file |
| `--limit`, `-n` | Process at most N units in a stage |
| `--dry-run` | Validate without writing outputs |
| `--tier` | Evaluation tier: `mvp` or `extended` |

No generic `--set key=value` override exists, although older docs mention it as a planned nicety.
