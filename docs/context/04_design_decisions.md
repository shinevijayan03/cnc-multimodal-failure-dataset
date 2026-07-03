# Architecture Decision Records

Only accepted technical decisions with repository evidence are recorded here.

## ADR-001: Use a Python CLI Pipeline

Decision:
- Use a Python Typer CLI as the main orchestration interface.

Context:
- The project has multiple ETL stages and evaluation commands.

Alternatives considered:
- Unknown; no repository evidence documents rejected alternatives.

Reason:
- Typer commands in `src/cli.py` expose clear stage operations and integrate with tests.

Impact:
- Users can run each stage independently or run `all`.

Status:
- Accepted and implemented.

Evidence:
- `src/cli.py`, `pyproject.toml`, `python -m src.cli --help`.

## ADR-002: Use Local File and Parquet Contracts

Decision:
- Use local filesystem paths and Parquet artifacts for generated dataset contracts.

Context:
- Config points raw and processed data to `data_pipeline/*`.

Alternatives considered:
- Unknown; no database-backed implementation exists.

Reason:
- Parquet supports tabular contract artifacts and is directly read by the CLI, evaluator, tests, and UI.

Impact:
- Refactoring must preserve artifact schemas unless explicitly approved.

Status:
- Accepted and implemented.

Evidence:
- `config/dataset.yaml`, `src/common/io_utils.py`, generated `data_pipeline/data_processed/*.parquet`.

## ADR-003: Use Pydantic Models for Configuration and Row Contracts

Decision:
- Use Pydantic for config validation and row schema models.

Context:
- ETL stages share structured config and output contracts.

Alternatives considered:
- Unknown.

Reason:
- Pydantic models validate config and row fields in tests and runtime helpers.

Impact:
- Schema changes require coordinated tests and generated artifact compatibility checks.

Status:
- Accepted and implemented.

Evidence:
- `src/common/config.py`, `src/common/schemas.py`, tests in `tests/unit/test_config.py` and `tests/unit/test_schemas.py`.

## ADR-004: Keep Streamlit UI Thin

Decision:
- Keep UI display logic in `streamlit_app.py` and data-loading/display helper logic in `src/ui/incident_explorer.py`.

Context:
- The UI needs to read Parquet artifacts and render incident evidence.

Alternatives considered:
- Unknown.

Reason:
- Helper functions are testable without launching Streamlit.

Impact:
- UI refactors should preserve the helper layer and its tests.

Status:
- Accepted and implemented.

Evidence:
- `streamlit_app.py`, `src/ui/incident_explorer.py`, `tests/unit/test_incident_explorer.py`.

## ADR-005: Treat ffmpeg as an External Binary

Decision:
- Do not install ffmpeg via pip; expect it on PATH for video operations.

Context:
- Video normalization/probing uses ffmpeg/ffprobe.

Alternatives considered:
- Unknown.

Reason:
- `requirements.txt` explicitly notes ffmpeg/ffprobe are external binaries.

Impact:
- Runtime environment must provide ffmpeg for full video processing; tests cover missing-tool behavior.

Status:
- Accepted and implemented.

Evidence:
- `requirements.txt`, `src/etl/video_etl.py`, `tests/unit/test_video.py`, `ffmpeg -version`.

## ADR-006: Add TGFX Contracts Beside Recipe A Schemas

Decision:
- Implement TGFX Pydantic contracts in a new top-level `contracts` package rather than replacing `src.common.schemas`.

Context:
- The existing Recipe A pipeline and Streamlit app depend on `src.common.schemas` and current Parquet artifacts.
- The master prompt requires TGFX contracts in `contracts/`.

Alternatives considered:
- Replace existing Recipe A schemas directly. Rejected because it would be a broad rewrite and risk breaking existing application behavior.

Reason:
- Additive contracts satisfy the first TGFX contract-ratchet slice while preserving current runtime functionality.

Impact:
- Future TGFX modules can import `contracts.*`.
- Existing Recipe A code remains stable.

Current status:
- Accepted and implemented.

Evidence:
- `contracts/core.py`, `contracts/explanation.py`, `tests/contracts/`, full validation passing.
