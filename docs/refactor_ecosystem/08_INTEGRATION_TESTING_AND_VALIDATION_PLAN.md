# Integration Testing and Validation Plan

## Purpose

Define how the current and target system should be tested and validated across unit, integration, end-to-end, Streamlit, GPU, regression, smoke, and performance coverage.

## 11.1 Test Scope

| Scope | Current Status | Target |
|---|---|---|
| Unit tests | Present and passing | Keep green |
| Integration tests | Present and passing | Extend for UI services |
| End-to-end smoke tests | Present with synthetic data | Add real ffmpeg path when available |
| Streamlit UI tests | Missing | Add after UI implementation |
| GPU tests | Missing | Add only after GPU abstraction/features |
| Regression tests | Present through existing suite | Add golden outputs for key fixtures if needed |
| Performance tests | Missing | Add scale/benchmark scripts for thesis build |

## 11.2 Test Environment

| Item | Current Finding |
|---|---|
| OS | Windows workstation |
| Python | 3.12.7 locally; CI covers 3.10-3.13 |
| Install command | `python -m pip install -r requirements.txt` |
| Test command | `python -m pytest -q` |
| GPU | RTX 3060 available through PyTorch |
| CUDA | Driver reports CUDA 13.2; PyTorch build cu124 |
| ffmpeg | Missing locally |
| Raw data | Not staged in repo |
| Environment variables | None required by current code |

## 11.3 Test Command Matrix

| Test Type | Command | Purpose | Expected Result |
|---|---|---|---|
| Unit/integration suite | `python -m pytest -q` | Validate current code | 76 passed |
| Collection | `python -m pytest --collect-only -q` | Verify test discovery | 76 tests collected |
| Compile smoke | `python -m compileall -q src tests` | Syntax/import smoke | Pass |
| CLI help | `python -m src.cli --help` | Validate CLI registration | Pass |
| Dry-run smoke | `python -m src.cli all --config config/dataset.yaml --dry-run --limit 1` | Validate config and no-data behavior | Nonzero until raw data exists |
| Evaluation smoke | `python -m src.cli evaluate --config config/dataset.yaml --tier mvp` | Validate report command | Nonzero until incidents exist |
| Lint | `python -m ruff check src tests` | Code quality | Currently 8 findings |
| Streamlit smoke | `streamlit run streamlit_app.py` | UI launch | Target Stage B |
| GPU check | Python torch CUDA check | Device readiness | PyTorch CUDA true |

## 11.4 Integration Scenarios

### Scenario: Sensor Stage on Synthetic CSV

Purpose:
Validate raw CSV to sensor windows.

Preconditions:
Temp workspace fixture with synthetic bursts.

Steps:
1. Load mini config.
2. Run `SensorETL.run()`.
3. Read sensor index and window files.

Expected Result:
Three windows and a valid sensor index are written.

Failure Signals:
No events, invalid Parquet, missing `t_rel_s`.

Logs/Artifacts:
`sensor_windows.parquet`, `sensor_windows/*.parquet`.

### Scenario: Text Stage on Synthetic Manual

Purpose:
Validate document chunking and tagging.

Preconditions:
Temp workspace fixture with markdown manual.

Steps:
1. Run `TextETL.run()`.
2. Read `text_chunks.parquet`.

Expected Result:
Chunks have unique IDs, valid doc types, token counts, and topic tags.

Failure Signals:
No chunks, duplicate IDs, unsupported doc type.

Logs/Artifacts:
`text_chunks.parquet`.

### Scenario: Assembly Without Video

Purpose:
Validate graceful missing-video behavior.

Preconditions:
Sensor and text indices exist, no video index.

Steps:
1. Run `IncidentAssembler.run()`.
2. Inspect summary and incidents.

Expected Result:
Incidents are written, `video_file` is null, `no_video` summary count is set.

Failure Signals:
Assembly crashes due missing video index.

Logs/Artifacts:
`incidents.parquet`.

### Scenario: Full Synthetic E2E

Purpose:
Validate end-to-end contracts on tiny data.

Preconditions:
Mini config and synthetic raw fixtures.

Steps:
1. Run sensor.
2. Run text.
3. Run assemble.
4. Read incidents.

Expected Result:
Incidents exist with unique IDs and split assignments.

Failure Signals:
Dangling chunk IDs, malformed JSON, duplicate incidents.

Logs/Artifacts:
All generated Parquet indices.

### Scenario: Evaluation

Purpose:
Validate metrics/report computation.

Preconditions:
`incidents.parquet`, sensor index, and text chunks exist.

Steps:
1. Run `evaluate_build`.
2. Inspect metrics and report files.

Expected Result:
Metrics include incident count, text completeness, missing-file rates, and reports are written.

Failure Signals:
Crash, missing report, false hard-gate failure on fixture.

Logs/Artifacts:
`eval_report.json`, `eval_report.md`.

### Scenario: Streamlit UI Smoke

Purpose:
Validate future UI imports and launches.

Preconditions:
Stage B UI implemented.

Steps:
1. Run UI import smoke test.
2. Launch Streamlit locally.
3. Load default config.

Expected Result:
UI renders status and diagnostics without running heavy ETL on import.

Failure Signals:
Import side effects, config crash, missing controls.

Logs/Artifacts:
Streamlit logs and screenshots if Playwright is added.

### Scenario: GPU CPU Fallback

Purpose:
Validate future device utility behavior.

Preconditions:
Stage B GPU utility implemented.

Steps:
1. Mock CUDA unavailable.
2. Request GPU.
3. Confirm CPU fallback and warning.

Expected Result:
No crash, selected device is CPU with reason.

Failure Signals:
ImportError crash, hard CUDA dependency, no fallback message.

Logs/Artifacts:
Device metadata.

## 11.5 Validation Checklist

- All generated Parquet contracts are readable.
- JSON-list columns decode correctly.
- No dangling chunk IDs.
- Missing-video cases are flagged, not hidden.
- Evaluation reports are generated after assembly.
- CLI commands and UI controls use the same backend behavior.
- GPU path, if implemented, has CPU fallback.
- Documentation commands match verified behavior.
