# Test Inventory

## Purpose

Record the discovered test framework, test cases, commands, and Stage A verification results.

## Test Framework

| Area | Current State |
|---|---|
| Framework | pytest |
| Config | `[tool.pytest.ini_options]` in `pyproject.toml` |
| Test roots | `tests/` |
| Markers | `ffmpeg` marker declared |
| Test fixtures | Synthetic temp-workspace fixtures in `tests/conftest.py` |
| CI command | `pytest -q --cov=src --cov-report=term-missing` |

## Test Layout

| Directory/File | Scope |
|---|---|
| `tests/unit/test_config.py` | Config loading and validation |
| `tests/unit/test_schemas.py` | Pydantic row schemas and JSON-list serialization |
| `tests/unit/test_io_ids.py` | Atomic IO, JSON helpers, deterministic IDs |
| `tests/unit/test_sensor.py` | Normalization, fs estimation, event detection, windows, spans |
| `tests/unit/test_text.py` | Tokenizer, chunking, doc reader, topic tagging |
| `tests/unit/test_video.py` | Probe parsing, ffmpeg command construction, tags, errors |
| `tests/unit/test_assemble.py` | Labeling, video matching, text retrieval, split assignment |
| `tests/integration/test_integration.py` | Stage run methods, assembly, evaluation, CLI and e2e smoke |
| `tests/conftest.py` | Synthetic sensor/manual fixtures and index factories |

## Collected Tests

`python -m pytest --collect-only -q` collected 76 tests.

## Stage A Verification Results

| Check | Command | Result |
|---|---|---|
| Full pytest suite | `python -m pytest -q` | 76 passed in 22.49s |
| Compile smoke | `python -m compileall -q src tests` | Passed |
| CLI help | `python -m src.cli --help` | Passed |
| Dry-run all with repo config | `python -m src.cli all --config config/dataset.yaml --dry-run --limit 1` | Expected nonzero: no raw data/index for assembly |
| Evaluate with repo config | `python -m src.cli evaluate --config config/dataset.yaml --tier mvp` | Expected nonzero: no `incidents.parquet` |
| Advisory lint | `python -m ruff check src tests` | Failed with 8 unused import/variable findings |

## Existing Test Strengths

- Numeric core has focused unit coverage.
- Integration tests build synthetic sensor and text inputs in temporary workspaces.
- Assembly is tested with and without video.
- Evaluation metrics are tested over generated fixture outputs.
- CLI behavior is covered through Typer's `CliRunner`.
- The suite is independent of licensed raw data.

## Test Gaps

| Gap | Impact | Recommended Stage B Action |
|---|---|---|
| No Streamlit UI tests | UI does not exist yet | Add smoke tests once Streamlit app exists |
| No GPU tests | GPU support not implemented | Add device-selection and CPU fallback tests if GPU path is added |
| No real ffmpeg integration in local run | ffmpeg missing | Install ffmpeg and add a marked video normalization test path |
| No thesis-scale performance tests | Scale targets unvalidated | Add benchmark/acceptance scripts for larger raw data builds |
| Lint not clean | CI advisory only, but polish gap remains | Fix unused imports/variable in Stage B |
