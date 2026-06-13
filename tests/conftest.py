"""Shared fixtures and synthetic-data factories.

All fixtures are tiny and generated in-process — no licensed data in the repo.
A `workspace` builds a temp mini-pipeline (sensor csv + manual + config) that the
integration tests run end-to-end; `make_*` factories build indices directly so
the assembler can be tested without running the upstream stages.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.common.config import load_config
from src.common.io_utils import rows_to_df
from src.common.schemas import SensorWindowRow, TextChunkRow, VideoIndexRow


# --------------------------------------------------------------------------- #
# Signal / document factories
# --------------------------------------------------------------------------- #
def make_bursts_df(fs: float = 2000.0, dur: float = 20.0,
                   burst_times=(5.0, 10.0, 15.0), burst_amp: float = 12.0,
                   noise: float = 1.0, dc: float = -1015.0, seed: int = 0,
                   burst_dur: float = 0.6) -> pd.DataFrame:
    """Tri-axial accel with K Gaussian bursts on `z`, plus a DC mounting offset
    (mimics the real Bosch corpus). Raw columns x/y/z for column_map testing."""
    n = int(dur * fs)
    rng = np.random.default_rng(seed)
    z = rng.normal(0, noise, n)
    for tc in burst_times:
        i = int(tc * fs)
        w = int(burst_dur * fs)
        z[i:i + w] += rng.normal(0, burst_amp, w)
    return pd.DataFrame({
        "x": rng.normal(0, noise, n),
        "y": rng.normal(0, noise, n),
        "z": z + dc,
    })


TINY_MANUAL_MD = """# Operating Procedure
Set up the workpiece and fixture before starting. Follow the startup procedure
and check the spindle speed and feed rate for each operation.

# Maintenance and Service
Inspect the spindle bearing for tool wear and chatter. If you observe heavy
vibration or chatter, replace the worn tool and check the coolant flow. Clean
and lubricate the slides during scheduled maintenance to avoid clamping issues.
"""

# Mini config tuned so the 3 synthetic bursts each yield a full window in a 20 s
# recording (small pre/post; zscore detector; bursts are 5 s apart).
MINI_YAML = """
version: 0.1.0
random_seed: 1337
paths:
  data_raw: data_raw
  data_processed: data_processed
  raw_sensor_root: data_raw
  raw_video_root: data_raw/video_raw
  raw_text_root: data_raw/text_manuals
  sensor_windows_dir: data_processed/sensor_windows
  sensor_index: data_processed/sensor_windows.parquet
  video_dir: data_processed/video
  video_index: data_processed/video_index.parquet
  text_chunks: data_processed/text_chunks.parquet
  incidents_index: data_processed/incidents.parquet
  logs_dir: logs
sensor:
  datasets:
    - name: demo
      enabled: true
      path: data_raw/demo
      reader: generic_csv
      machine_family: cnc_mill
      fs_hz: 2000
      column_map: { x: ax, y: ay, z: az }
    - name: disabled_ds
      enabled: false
      path: data_raw/none
      reader: generic_csv
      fs_hz: 2000
      column_map: { x: ax, y: ay, z: az }
  canonical_channels: [time_s, ax, ay, az]
  optional_channels: []
  fs_estimation: { method: median_dt, min_plausible_hz: 100, max_plausible_hz: 100000 }
  event_detection:
    method: rms_threshold
    channel_for_energy: az
    window_s: 0.5
    hop_s: 0.1
    threshold_kind: zscore
    threshold_value: 4.0
    baseline_window_s: 5.0
    min_event_separation_s: 1.0
    min_event_duration_s: 0.1
  windowing: { pre_event_s: 3.0, post_event_s: 2.0, drop_partial_windows: true }
  evidence_spans: { method: threshold_crossings, pad_s: 0.5, max_spans: 5 }
text:
  input_formats: [md, markdown, txt, docx, pdf]
  chunking:
    target_tokens: 30
    min_tokens: 0
    max_tokens: 60
    overlap_tokens: 5
    respect_headings: true
    tokenizer: whitespace
  doc_types: [sop, maintenance]
  topic_keywords:
    vibration: [vibration, chatter]
    tool_wear: [tool wear, worn]
    coolant: [coolant]
    spindle: [spindle, bearing]
    clamping: [clamping, fixture]
assemble:
  video_match:
    strategy: label_match
    require_regime_match: false
    require_condition_match: false
    allow_reuse: true
    fallback_to_idle: true
  text_retrieval:
    method: keyword_bm25
    sop_chunks_min: 1
    sop_chunks_max: 2
    maintenance_chunks_min: 1
    maintenance_chunks_max: 2
    failure_to_topics:
      unknown: [vibration, tool_wear]
  default_label: unknown
  split:
    strategy: grouped_by_source
    fractions: { train: 0.7, val: 0.15, test: 0.10, human_eval: 0.05 }
    group_key: source_dataset
runtime:
  log_level: WARNING
  log_format: text
  fail_fast: false
"""


# --------------------------------------------------------------------------- #
# Workspace fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A temp repo: config/ + data_raw with one sensor csv and one manual."""
    (tmp_path / "config").mkdir()
    (tmp_path / "data_raw" / "demo").mkdir(parents=True)
    (tmp_path / "data_raw" / "text_manuals").mkdir(parents=True)
    (tmp_path / "data_raw" / "video_raw").mkdir(parents=True)
    make_bursts_df().to_csv(tmp_path / "data_raw" / "demo" / "run1.csv", index=False)
    (tmp_path / "data_raw" / "text_manuals" / "tiny_manual.md").write_text(
        TINY_MANUAL_MD, encoding="utf-8")
    (tmp_path / "config" / "dataset.yaml").write_text(MINI_YAML, encoding="utf-8")
    return tmp_path


@pytest.fixture
def mini_cfg(workspace: Path):
    return load_config(workspace / "config" / "dataset.yaml")


# --------------------------------------------------------------------------- #
# Index factories (build indices directly, no upstream stages)
# --------------------------------------------------------------------------- #
def make_sensor_index(n: int = 3, source: str = "demo") -> pd.DataFrame:
    rows = [
        SensorWindowRow(
            incident_id=f"inc_{source}_{i:03d}",
            source_dataset=source,
            machine_family="cnc_mill",
            window_start_s=float(i * 100),
            window_end_s=float(i * 100 + 90),
            fs_hz=2000.0,
            sensor_file=f"data_processed/sensor_windows/inc_{source}_{i:03d}.parquet",
            sensor_channels=["ax", "ay", "az"],
            sensor_relevant_spans=[],
            n_samples=180001,
        )
        for i in range(n)
    ]
    return rows_to_df(rows)


def make_video_index(regimes=("roughing", "idle", "finishing")) -> pd.DataFrame:
    rows = [
        VideoIndexRow(
            video_id=f"vid_{i:03d}",
            video_file=f"data_processed/video/vid_{i:03d}.mp4",
            video_fps=30.0,
            duration_s=7.0,
            regime_label=r,
            condition_label="normal",
            source="own",
        )
        for i, r in enumerate(regimes)
    ]
    return rows_to_df(rows)


def make_chunks(n_sop: int = 4, n_maint: int = 4) -> pd.DataFrame:
    rows = []
    for i in range(n_sop):
        rows.append(TextChunkRow(
            doc_id="doc_a", chunk_id=f"doc_a__c{i:04d}", doc_type="sop",
            text=f"operating procedure chunk {i} about feed rate and setup",
            topic_tags=["vibration"] if i % 2 == 0 else ["tool_wear"], n_tokens=30))
    for i in range(n_maint):
        rows.append(TextChunkRow(
            doc_id="doc_b", chunk_id=f"doc_b__c{i:04d}", doc_type="maintenance",
            text=f"maintenance chunk {i} inspect spindle bearing wear",
            topic_tags=["spindle"] if i % 2 == 0 else ["tool_wear"], n_tokens=30))
    return rows_to_df(rows)
