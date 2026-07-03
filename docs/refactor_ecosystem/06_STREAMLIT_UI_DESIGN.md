# Streamlit UI Design

## Purpose

Design a Streamlit UI layer for the CNC multimodal dataset pipeline. This is a Stage A design only. No UI was implemented before approval.

## Current UI Assessment

| Check | Result |
|---|---|
| Existing Streamlit app | None found |
| Streamlit imports/usages in repo | None found |
| Streamlit dependency declared | Not in `pyproject.toml` or `requirements.txt` |
| Streamlit installed locally | Yes |
| Current user interface | Typer CLI |

## UI Purpose

Provide a local operator dashboard for users who want to inspect configuration, check environment readiness, run ETL stages, review outputs, and view evaluation summaries without remembering every CLI command.

## Target Users

- Thesis author building the dataset locally
- Reviewers validating pipeline readiness
- Developers debugging staged raw data, config, ffmpeg, optional dependencies, and outputs

## Recommended Location

Prefer root-level app for the simplest run command:

```text
streamlit_app.py
```

Run command:

```bash
streamlit run streamlit_app.py
```

If a package-based UI is preferred later:

```text
src/ui/streamlit_app.py
```

Run command:

```bash
streamlit run src/ui/streamlit_app.py
```

## Backend Integration Pattern

Streamlit should call backend services, not own ETL logic.

Proposed Stage B support module:

```text
src/services/pipeline_runner.py
src/services/diagnostics.py
```

Responsibilities:

- Load config
- Run one stage or all stages
- Return `RunSummary` objects
- Check raw data presence
- Check ffmpeg/ffprobe
- Check optional dependencies
- Check GPU status
- Locate output artifacts

## Pages and Navigation

| Page | Purpose | Key Outputs |
|---|---|---|
| Overview | Show project status, selected config, output presence | Current config path, output cards, stage readiness |
| Configuration | Inspect `dataset.yaml` sections | Validated config summary, path resolution table |
| Run Pipeline | Run individual stages or full pipeline | Progress, summaries, errors |
| Evaluation | Run/view `evaluate` report | Metrics table, grade, warnings/failures |
| Outputs | Browse generated artifacts | DataFrame previews and download links |
| Diagnostics | Check environment | ffmpeg, optional deps, GPU, Python version, raw-data presence |

## Input Controls

| Control | Type | Purpose |
|---|---|---|
| Config path | Text input or file picker | Choose YAML config |
| Stage selector | Segmented control or selectbox | Choose sensor/text/video/assemble/all/evaluate |
| Limit | Number input | Run smaller smoke batches |
| Dry run | Toggle | Validate without writes |
| Evaluation tier | Segmented control | mvp vs extended |
| Prefer GPU | Toggle | Only active if GPU feature is implemented |
| Run button | Button | Execute selected action |
| Refresh diagnostics | Button | Recheck environment |

## Output Views

- Stage `RunSummary` table
- Logs/status messages
- Config path resolution table
- Output artifact presence table
- Evaluation metric table
- Markdown report preview
- DataFrame preview of Parquet outputs
- Download buttons for evaluation reports and small CSV previews

## Status and Progress

Use Streamlit status containers:

- Show "ready", "running", "skipped", "failed", "completed" per stage.
- Surface known skip reasons, especially missing ffmpeg or no raw data.
- Show errors without stack traces by default, with an expandable technical details block.

## Error Display Strategy

| Error | UI Response |
|---|---|
| Invalid config | Show ConfigError message and offending key |
| Missing raw data | Show staging checklist and expected folder |
| Missing ffmpeg | Show install hint and note video stage skip behavior |
| Missing `incidents.parquet` | Prompt user to run assemble or full pipeline |
| Optional dependency missing | Explain fallback or skipped format |
| GPU unavailable | Disable GPU toggle or show CPU fallback |

## GPU Toggle

Current project code does not use GPU. The UI should include a disabled or informational GPU panel until a real GPU-backed feature exists. After Stage B GPU work, the toggle should map to a backend `prefer_gpu` flag.

## File Upload/Download

Do not upload large raw datasets into Streamlit memory by default. Prefer path-based staging under `data_raw`. Small config upload can be supported later.

Downloads:

- `eval_report.md`
- `eval_report.json`
- Small CSV preview exports of generated Parquet tables

## Visual Style

This is an operational data pipeline UI, so use a quiet, dense layout:

- Sidebar for config/stage controls
- Main area for status, tables, and reports
- Tabs for outputs and diagnostics
- Avoid marketing-style hero sections
- Keep long logs in expanders

## Tests Required

| Test | Purpose |
|---|---|
| Import smoke | UI imports without executing stages |
| Diagnostics service tests | Verify ffmpeg/dependency/GPU checks can be mocked |
| Runner service tests | Verify stage selection maps to correct ETL class |
| Config error display test | Invalid config is surfaced safely |
| Output discovery test | Missing/present artifacts are reported correctly |

## Stage B Acceptance Criteria

- User can launch Streamlit with one documented command.
- User can load the default config.
- UI shows raw-data, ffmpeg, optional dependency, and output readiness.
- User can run at least dry-run/smoke commands from the UI.
- User can view evaluation reports when present.
- UI does not duplicate ETL business logic.
