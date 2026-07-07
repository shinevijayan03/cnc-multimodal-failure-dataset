# Runtime Execution Report

## Runtime Entry Points

| Entry Point | Command | Evidence | Status |
|---|---|---|---|
| CLI help | `python -m src.cli --help` | listed commands `sensor`, `text`, `video`, `assemble`, `all`, `evaluate` | Pass |
| Evaluation | `python -m src.cli evaluate --config config/dataset.yaml --tier mvp` | exited 0 with grade `WARN` and metrics | Pass with data warnings |
| Streamlit UI | `python -m streamlit run streamlit_app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false` | process PID `9016`; HTTP 200 | Pass |

## Application Execution State

Classification: Runs successfully, with data-quality warnings.

Evidence:
- Streamlit process:
  - PID: `9016`.
  - Path: `C:\ProgramData\anaconda3\python.exe`.
  - Command line: `python -m streamlit run streamlit_app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false`.
- Endpoint check:
  - `Invoke-WebRequest -Uri http://localhost:8501 -UseBasicParsing -TimeoutSec 15`
  - Result: `HTTP_STATUS=200`, `CONTENT_LENGTH=1522`.
- Streamlit log:
  - `Local URL: http://localhost:8501`
  - `Network URL: http://192.168.88.9:8501`
  - `External URL: http://49.207.203.136:8501`

Revalidation on 2026-07-02 20:06 Asia/Calcutta:
- `Invoke-WebRequest -Uri http://localhost:8501 -UseBasicParsing -TimeoutSec 15` returned `HTTP_STATUS=200`, `CONTENT_LENGTH=1522`.
- Port 8501 still has listener process PID `9016`.

## Processed Artifact Availability

Command:
- Python/pandas row-count script over `data_pipeline/data_processed`.

Results:

| Artifact | Rows | Columns | Bytes | Status |
|---|---:|---:|---:|---|
| `incidents.parquet` | 1702 | 21 | 81931 | Present |
| `sensor_windows.parquet` | 1702 | 11 | 73666 | Present |
| `text_chunks.parquet` | 934 | 6 | 319234 | Present |
| `video_index.parquet` | 20 | 7 | 5284 | Present |

## Evaluation Runtime

Command:
- `python -m src.cli evaluate --config config/dataset.yaml --tier mvp`.

Result:
- Exit code: 0.
- Grade: `WARN`.

Key metrics:
- `n_incidents`: 1702.
- `total_incident_hours`: 7.5617.
- `n_video_clips`: 20.
- `text_pages_equiv`: 319.07.
- `pct_fully_multimodal`: 1.0.
- `pct_missing_sensor_file`: 0.0.
- `pct_missing_video_file`: 0.0.
- `pct_dangling_chunk_id`: 0.0.
- `pct_duplicate_incident_id`: 0.0.

Warnings:
- `dominant_class_share=1.0 misses <=0.8`.
- `pct_unknown_failure=1.0 misses <=0.7`.
- `entropy_failure=0.0 misses >=0.3`.

Interpretation:
- The runtime can evaluate the dataset, but label diversity and unknown failure labels are not yet thesis-quality.

## Pipeline Dry-Run Runtime

Command:
- `python -m src.cli all --config config/dataset.yaml --dry-run --limit 2`.

Result:
- Timed out after 124 seconds.

Stage isolation:
- `python -m src.cli sensor --config config/dataset.yaml --dry-run --limit 2`
  - Pass: `[sensor] [DRY-RUN] discovered=0 processed=2 written=2 skipped=1 errors=0 | incident_hours=0.0089`.
- `python -m src.cli text --config config/dataset.yaml --dry-run --limit 2`
  - Timed out after 64 seconds and left a Python process running.
- `python -m src.cli video --config config/dataset.yaml --dry-run --limit 2`
  - Pass: `[video] [DRY-RUN] discovered=20 processed=2 written=0 skipped=0 errors=0 | duration_flagged=2`.
- `python -m src.cli assemble --config config/dataset.yaml --dry-run --limit 2`
  - Pass: `[assemble] [DRY-RUN] discovered=2 processed=2 written=0 skipped=0 errors=0 | no_video=0 short_text=0 split_groups=1`.

Follow-up:
- Orphan text dry-run process PID `38176` was stopped.

Revalidation on 2026-07-02 20:06 Asia/Calcutta:
- `text --dry-run --limit 2` timed out again after 64 seconds.
- New orphan text dry-run process PID `37436` was stopped.

Inference:
- The text dry-run bottleneck is likely document/PDF parsing or tokenization before the limit boundary completes two documents. Evidence: `TextETL.run()` reads and chunks whole discovered documents, and `data_pipeline/data_raw/text_manuals` contains PDF manuals.

## Missing Environment Variables or Services

Finding:
- No missing environment variables or external services were reported during setup, CLI help, evaluation, tests, or Streamlit HTTP check.

Unknown:
- Full browser-level UI interaction was not tested with Playwright or manual clicking in this audit.
