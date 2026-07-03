# Pipeline Runbook and Build Results

## Purpose

Record the implemented pipeline changes, the current dataset build result, and the exact commands to rerun when new data arrives.

## Implemented Changes

| Area | Change |
|---|---|
| Active config | `config/dataset.yaml` now points to `data_pipeline/data_raw` and `data_pipeline/data_processed` |
| Sensor config | `kaggle_cnc` uses `data_pipeline/data_raw/sensor_dataset`; missing Bosch H5 is disabled |
| Sensor windowing | Uses 8 seconds before and 8 seconds after the event, `drop_partial_windows: false`, and `max_windows_per_run: 1` |
| Sensor event mode | Added `segment_center` mode for short operation-segment CSV files |
| Text config | Added `text.max_pages_per_doc: 80` to cap large PDF manuals |
| Video ingestion | Discovers `.mp4`, `.mov`, `.m4v`, `.avi`, `.mkv`, and `.webm` recursively |
| Video fallback | If ffmpeg/ffprobe are missing, the pipeline writes a raw video index instead of skipping all videos |
| Local ffmpeg install | `Gyan.FFmpeg` 8.1.1 installed with winget and verified on PATH |
| Output paths | Sensor/video file paths are stored repo-relative to the actual configured output locations |
| Git ignore | `data_pipeline/data_raw`, `data_pipeline/data_processed`, and `data_pipeline/logs` are ignored |
| Tests/lint | Added tests for raw video fallback and segment-center mode; cleaned ruff findings |

## Current Staged Raw Data

| Modality | Folder | Count |
|---|---|---:|
| Sensor CSV | `data_pipeline/data_raw/sensor_dataset` | 1,702 CSV files |
| Text PDF manuals | `data_pipeline/data_raw/text_manuals` | 5 PDF files |
| Video clips | `data_pipeline/data_raw/video_raw` | 20 MP4 files |
| Video tag template | `data_pipeline/data_raw/video_raw/video_tags.csv` | 20 rows |

## Build Commands

Run the full pipeline:

```bash
python -m src.cli all --config config/dataset.yaml
```

Run evaluation:

```bash
python -m src.cli evaluate --config config/dataset.yaml --tier mvp
```

Launch the incident explorer UI:

```bash
streamlit run streamlit_app.py
```

Run tests:

```bash
python -m pytest -q
python -m ruff check src tests
python -m compileall -q src tests
```

## Current Build Result

The full build completed successfully on 2026-06-20.

| Output | Path | Rows/Files |
|---|---|---:|
| Sensor windows index | `data_pipeline/data_processed/sensor_windows.parquet` | 1,702 rows |
| Sensor window files | `data_pipeline/data_processed/sensor_windows/*.parquet` | 1,702 files |
| Text chunks index | `data_pipeline/data_processed/text_chunks.parquet` | 934 rows |
| Video index | `data_pipeline/data_processed/video_index.parquet` | 20 rows |
| Normalized video clips | `data_pipeline/data_processed/video/*.mp4` | 20 files |
| Incident dataset | `data_pipeline/data_processed/incidents.parquet` | 1,702 rows |
| Evaluation JSON | `data_pipeline/data_processed/eval_report.json` | generated |
| Evaluation Markdown | `data_pipeline/data_processed/eval_report.md` | generated |

## Evaluation Summary

Evaluation command:

```bash
python -m src.cli evaluate --config config/dataset.yaml --tier mvp
```

Result:

```text
GRADE: WARN
n_incidents: 1702
total_incident_hours: 7.5617
n_video_clips: 20
text_pages_equiv: 319.07
pct_fully_multimodal: 1.0
pct_missing_sensor_file: 0.0
pct_missing_video_file: 0.0
pct_dangling_chunk_id: 0.0
pct_duplicate_incident_id: 0.0
pct_bad_span: 0.0
```

Warnings:

- `failure_family` is currently `unknown` for all 1,702 incidents.
- `regime_label` is currently `unknown` for all 1,702 incidents.
- Failure-class entropy is 0 because no failure taxonomy labels are assigned yet.

This is acceptable as a first data-pipeline build because all hard integrity gates passed. The next modeling-quality step is to improve labels and video tags.

## How to Add New Data

### Add Sensor CSV Files

Place new CSV files anywhere under:

```text
data_pipeline/data_raw/sensor_dataset/
```

Expected columns:

```text
x,y,z
```

Then rerun:

```bash
python -m src.cli sensor --config config/dataset.yaml
python -m src.cli assemble --config config/dataset.yaml
python -m src.cli evaluate --config config/dataset.yaml --tier mvp
```

### Add Text Manuals

Place Markdown, text, DOCX, or PDF files under:

```text
data_pipeline/data_raw/text_manuals/
```

Then rerun:

```bash
python -m src.cli text --config config/dataset.yaml
python -m src.cli assemble --config config/dataset.yaml
python -m src.cli evaluate --config config/dataset.yaml --tier mvp
```

Large PDFs are capped by:

```yaml
text:
  max_pages_per_doc: 80
```

### Add Video Files

Place video files anywhere under:

```text
data_pipeline/data_raw/video_raw/
```

Supported discovery extensions:

```text
.mp4, .mov, .m4v, .avi, .mkv, .webm
```

Edit:

```text
data_pipeline/data_raw/video_raw/video_tags.csv
```

Allowed `regime` values:

```text
roughing, finishing, plunge, idle, drilling, contouring, unknown
```

Allowed `condition` values:

```text
normal, tool_wear_visible, heavy_vibration, coolant_issue, chatter, chip_packing, unknown
```

Then rerun:

```bash
python -m src.cli video --config config/dataset.yaml
python -m src.cli assemble --config config/dataset.yaml
python -m src.cli evaluate --config config/dataset.yaml --tier mvp
```

## Video Tooling Status

ffmpeg is installed and verified on this machine:

```text
ffmpeg version 8.1.1-full_build-www.gyan.dev
ffprobe version 8.1.1-full_build-www.gyan.dev
```

The current 20 videos were normalized into:

```text
data_pipeline/data_processed/video/
```

They are still flagged by the video stage because their duration is about 2.8 seconds, while the current config expects clips between 5 and 10 seconds:

```yaml
video:
  normalize:
    clip_min_s: 5
    clip_max_s: 10
```

To change that policy for short demo clips, lower `clip_min_s` and rerun:

```bash
python -m src.cli video --config config/dataset.yaml
python -m src.cli assemble --config config/dataset.yaml
python -m src.cli evaluate --config config/dataset.yaml --tier mvp
```

## Recommended Next Step

Move to label improvement:

1. Edit `data_pipeline/data_raw/video_raw/video_tags.csv`.
2. Decide how to map `good` and `bad` sensor folders to failure labels, if at all.
3. Consider adding a metadata-derived label step so `failure_family`, `regime_label`, and `root_cause_label` are not all `unknown`.
4. Rerun assembly and evaluation.
