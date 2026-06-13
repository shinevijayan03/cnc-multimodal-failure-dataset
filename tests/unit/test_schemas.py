"""Schema tests — UT-SCH-01..05."""

from __future__ import annotations

import pandas as pd
import pytest
from pydantic import ValidationError

from src.common.io_utils import load_json_col, model_to_record, rows_to_df, write_parquet_atomic
from src.common.schemas import IncidentRow, SensorWindowRow, Span, Split


def _incident(**over):
    base = dict(
        incident_id="inc_1", source_dataset="demo", machine_family="cnc_mill",
        failure_family="unknown", window_start_s=0.0, window_end_s=90.0, fs_hz=2000.0,
        sensor_file="data_processed/sensor_windows/inc_1.parquet",
        sensor_channels=["ax", "ay", "az"],
        sensor_relevant_spans=[Span(start_s=-1.0, end_s=1.0)],
        split="train",
    )
    base.update(over)
    return IncidentRow(**base)


def test_valid_sensor_window_row():  # UT-SCH-01
    row = SensorWindowRow(
        incident_id="i", source_dataset="d", machine_family="cnc_mill",
        window_start_s=0.0, window_end_s=90.0, fs_hz=2000.0, sensor_file="f.parquet",
        sensor_channels=["az"])
    assert row.failure_family.value == "unknown"      # default applied
    assert row.sensor_relevant_spans == []            # default optional


def test_span_ordering():  # UT-SCH-02
    with pytest.raises(ValidationError):
        Span(start_s=5.0, end_s=2.0)


def test_bad_enum():  # UT-SCH-03
    with pytest.raises(ValidationError):
        _incident(regime_label="spin")


def test_json_list_round_trip(tmp_path):  # UT-SCH-04
    row = _incident(
        sensor_relevant_spans=[Span(start_s=-2.0, end_s=0.5), Span(start_s=1.0, end_s=3.0)],
        sop_chunk_ids=["a", "b"], maintenance_chunk_ids=["c"])
    df = rows_to_df([row])
    p = tmp_path / "inc.parquet"
    write_parquet_atomic(df, p)
    back = pd.read_parquet(p).iloc[0]
    spans = load_json_col(back["sensor_relevant_spans"])
    assert [(s["start_s"], s["end_s"]) for s in spans] == [(-2.0, 0.5), (1.0, 3.0)]
    assert load_json_col(back["sop_chunk_ids"]) == ["a", "b"]
    assert load_json_col(back["maintenance_chunk_ids"]) == ["c"]


def test_required_field_missing():  # UT-SCH-05
    with pytest.raises(ValidationError) as exc:
        IncidentRow(
            incident_id="i", source_dataset="d", machine_family="cnc_mill",
            failure_family="unknown", window_start_s=0.0, window_end_s=90.0,
            fs_hz=2000.0, sensor_file="f", sensor_channels=["az"],
            sensor_relevant_spans=[])  # no split
    assert "split" in str(exc.value)


def test_model_to_record_serializes_enums_and_lists():
    rec = model_to_record(_incident())
    assert rec["failure_family"] == "unknown"          # enum -> value
    assert isinstance(rec["sensor_channels"], str)     # list -> json string
    assert rec["split"] == "train"
    assert Split(rec["split"]) is Split.train
