"""Tests for Streamlit incident explorer data helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.common.io_utils import rows_to_df, write_parquet_atomic
from src.common.schemas import TextChunkRow
from src.ui.incident_explorer import (
    alignment_rows,
    available_sensor_channels,
    downsample_frame,
    incident_labels,
    incident_text_evidence,
    load_pipeline_tables,
    load_sensor_window,
    ordered_chunks,
    resolve_repo_path,
    sensor_plot_frame,
    video_path_for_display,
)


def test_resolve_repo_path_relative(tmp_path):
    assert resolve_repo_path("a/b.parquet", tmp_path) == tmp_path / "a" / "b.parquet"


def test_incident_labels_include_key_fields():
    incidents = pd.DataFrame([{
        "incident_id": "inc_001",
        "severity_label": "high",
        "failure_family": "chatter",
        "split": "test",
    }])
    labels = incident_labels(incidents)
    assert labels["inc_001"] == "inc_001 | severity=high | failure=chatter | split=test"


def test_ordered_chunks_preserves_incident_order():
    chunks = rows_to_df([
        TextChunkRow(doc_id="d", chunk_id="c1", doc_type="sop", text="one", n_tokens=1),
        TextChunkRow(doc_id="d", chunk_id="c2", doc_type="sop", text="two", n_tokens=1),
    ])
    out = ordered_chunks(chunks, ["c2", "c1"])
    assert list(out["chunk_id"]) == ["c2", "c1"]


def test_incident_text_evidence_splits_sop_and_maintenance():
    chunks = rows_to_df([
        TextChunkRow(doc_id="d", chunk_id="sop1", doc_type="sop", text="sop", n_tokens=1),
        TextChunkRow(
            doc_id="d",
            chunk_id="maint1",
            doc_type="maintenance",
            text="maint",
            n_tokens=1,
        ),
    ])
    incident = pd.Series({
        "sop_chunk_ids": '["sop1"]',
        "maintenance_chunk_ids": '["maint1"]',
    })
    sop, maint = incident_text_evidence(incident, chunks)
    assert list(sop["chunk_id"]) == ["sop1"]
    assert list(maint["chunk_id"]) == ["maint1"]


def test_load_pipeline_tables_and_sensor_window(tmp_path):
    processed = tmp_path / "data_processed"
    processed.mkdir()
    sensor_file = tmp_path / "sensor.parquet"
    sensor_df = pd.DataFrame({"time_s": [0.0, 0.5], "t_rel_s": [-0.5, 0.0], "ax": [1, 2]})
    write_parquet_atomic(sensor_df, sensor_file)
    incidents = pd.DataFrame([{
        "incident_id": "inc",
        "sensor_file": str(sensor_file),
        "sensor_relevant_spans": '[{"start_s": -0.5, "end_s": 0.0}]',
    }])
    write_parquet_atomic(incidents, processed / "incidents.parquet")

    tables = load_pipeline_tables(processed)
    path, loaded = load_sensor_window(tables.incidents.iloc[0], Path("/unused"))

    assert path == sensor_file
    pd.testing.assert_frame_equal(loaded, sensor_df)


def test_sensor_plot_frame_downsamples_and_indexes_time():
    df = pd.DataFrame({
        "t_rel_s": [0, 1, 2, 3],
        "time_s": [10, 11, 12, 13],
        "ax": [1, 2, 3, 4],
        "label": ["a", "b", "c", "d"],
    })
    assert available_sensor_channels(df) == ["ax"]
    out = sensor_plot_frame(df, ["ax"], max_points=2)
    assert list(out.columns) == ["ax"]
    assert len(out) == 2
    assert list(out.index) == [0, 2]


def test_downsample_frame_keeps_output_at_or_below_max_points():
    df = pd.DataFrame({"x": range(9999)})
    out = downsample_frame(df, max_points=5000)
    assert len(out) <= 5000


def test_video_path_for_display_treats_blank_values_as_missing(tmp_path):
    assert video_path_for_display(pd.Series({"video_file": ""}), tmp_path) is None
    assert video_path_for_display(pd.Series({"video_file": "   "}), tmp_path) is None


def test_alignment_rows_counts_evidence():
    incident = pd.Series({
        "sensor_file": "sensor.parquet",
        "video_file": "video.mp4",
        "alignment_method": "label_match",
        "sensor_relevant_spans": '[{"start_s": -1, "end_s": 1}]',
        "video_relevant_spans": '[{"start_s": 0, "end_s": 2}]',
        "sop_chunk_ids": '["s1", "s2"]',
        "maintenance_chunk_ids": '["m1"]',
    })
    rows = alignment_rows(incident)
    assert set(rows["modality"]) == {"sensor", "video", "SOP text", "maintenance text"}
    assert "2 chunk ids" in rows.loc[rows["modality"] == "SOP text", "artifact"].iloc[0]
