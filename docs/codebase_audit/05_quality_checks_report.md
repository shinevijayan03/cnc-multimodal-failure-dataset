# Quality Checks Report

## Summary

| Check | Command | Result | Evidence |
|---|---|---|---|
| Dependency install | `python -m pip install -r requirements.txt` | Pass | exit code 0, requirements already satisfied |
| CLI help | `python -m src.cli --help` | Pass | commands listed |
| ffmpeg availability | `ffmpeg -version` | Pass | `ffmpeg version 8.1.1-full_build-www.gyan.dev` |
| Test collection | `pytest --collect-only -q` | Pass | `87 tests collected in 4.43s` |
| Unit/integration tests with coverage | `pytest -q --cov=src --cov-report=term-missing` | Pass | `87 passed in 45.58s`, total coverage `82%` |
| Lint | `ruff check src tests` | Pass | `All checks passed!` |
| Python compile | `python -m compileall -q src streamlit_app.py` | Pass | exit code 0 |
| Dataset evaluation | `python -m src.cli evaluate --config config/dataset.yaml --tier mvp` | Pass with WARN grade | grade `WARN`; class/label warnings |
| Pipeline all dry-run | `python -m src.cli all --config config/dataset.yaml --dry-run --limit 2` | Timeout | timed out after 124 seconds |
| Text dry-run isolation | `python -m src.cli text --config config/dataset.yaml --dry-run --limit 2` | Timeout | timed out after 64 seconds |

Revalidation on 2026-07-02 20:06 Asia/Calcutta:
- `pytest --collect-only -q`: `87 tests collected in 2.55s`.
- `pytest -q --cov=src --cov-report=term-missing`: `87 passed in 58.95s`, total coverage `82%`.
- `ruff check src tests`: passed.
- `python -m compileall -q src streamlit_app.py`: passed.
- `python -m src.cli evaluate --config config/dataset.yaml --tier mvp`: grade `WARN`.
- `text --dry-run --limit 2`: timed out after 64 seconds again.

## Test Coverage Detail

From `pytest -q --cov=src --cov-report=term-missing`:

| Module | Coverage |
|---|---:|
| `src/__init__.py` | 100% |
| `src/cli.py` | 56% |
| `src/common/config.py` | 94% |
| `src/common/errors.py` | 100% |
| `src/common/ids.py` | 100% |
| `src/common/io_utils.py` | 84% |
| `src/common/logging_utils.py` | 83% |
| `src/common/schemas.py` | 100% |
| `src/etl/assemble_incidents.py` | 87% |
| `src/etl/sensor_etl.py` | 74% |
| `src/etl/text_etl.py` | 77% |
| `src/etl/video_etl.py` | 76% |
| `src/evaluate.py` | 94% |
| `src/ui/incident_explorer.py` | 80% |
| Total | 82% |

## Test Inventory

Evidence:
- `pytest --collect-only -q` collected 87 tests.
- Test files cover:
  - `tests/integration/test_integration.py`
  - `tests/unit/test_assemble.py`
  - `tests/unit/test_config.py`
  - `tests/unit/test_incident_explorer.py`
  - `tests/unit/test_io_ids.py`
  - `tests/unit/test_schemas.py`
  - `tests/unit/test_sensor.py`
  - `tests/unit/test_text.py`
  - `tests/unit/test_video.py`

## Build and Packaging

Finding:
- There is a `pyproject.toml` with setuptools metadata and a console script `recipe-a = "src.cli:app"`.
- This audit did not run `python -m build` because `build` is not declared in `requirements.txt` or CI.

Status:
- Packaging metadata exists, but build artifact generation is unverified.

## Lint and Static Checks

Finding:
- `ruff check src tests` passed locally.
- CI treats ruff as advisory via `continue-on-error: true`.

Risk:
- Lint passing locally is good, but advisory CI means future lint regressions would not block merges.

## Security and Dependency Checks

Finding:
- No security scanner is declared in `requirements.txt`, `pyproject.toml`, or `.github/workflows/ci.yml`.
- Source scan found no obvious secrets or environment-based credentials.

Unknown:
- Vulnerability status of installed packages was not checked because no native security tool is configured.

## Quality Baseline Decision

Baseline:
- Automated tests, lint, compile, dependency install, CLI help, evaluation, and Streamlit HTTP smoke all pass.

Primary issues:
- Dataset evaluation is `WARN` because label quality/diversity is weak.
- Text ETL dry-run with `--limit 2` times out, making `all --dry-run --limit 2` unreliable as a quick validation path.
- Build packaging is not verified by CI.
