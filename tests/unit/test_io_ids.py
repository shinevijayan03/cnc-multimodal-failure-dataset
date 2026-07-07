"""IO + ids tests — UT-IO-01..06, UT-ID-01..02."""

from __future__ import annotations

import os
import time

import pandas as pd
import pytest

from src.common import ids
from src.common.io_utils import (
    dump_json_col,
    exists_and_fresh,
    load_json_col,
    write_parquet_atomic,
)
from src.common.schemas import Span


def test_atomic_write_success(tmp_path):  # UT-IO-01
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    p = tmp_path / "out.parquet"
    write_parquet_atomic(df, p)
    assert p.exists()
    assert not list(tmp_path.glob("*.tmp"))                  # no temp left
    pd.testing.assert_frame_equal(pd.read_parquet(p), df)


def test_atomic_write_failure_leaves_original(tmp_path, monkeypatch):  # UT-IO-02
    p = tmp_path / "out.parquet"
    write_parquet_atomic(pd.DataFrame({"a": [1]}), p)
    original = p.read_bytes()

    def boom(self, *a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", boom)
    with pytest.raises(OSError):
        write_parquet_atomic(pd.DataFrame({"a": [2]}), p)
    assert p.read_bytes() == original                        # original intact
    assert not list(tmp_path.glob("*.tmp"))


def test_json_col_round_trip_span():  # UT-IO-03
    spans = [Span(start_s=-1.0, end_s=2.0), Span(start_s=3.0, end_s=3.5)]
    out = load_json_col(dump_json_col(spans))
    assert [(s["start_s"], s["end_s"]) for s in out] == [(-1.0, 2.0), (3.0, 3.5)]


def test_json_col_round_trip_str():  # UT-IO-04
    assert load_json_col(dump_json_col(["a", "b", "c"])) == ["a", "b", "c"]
    assert load_json_col(None) == []                         # null tolerated


def test_exists_and_fresh(tmp_path):  # UT-IO-05 / UT-IO-06
    inp = tmp_path / "in.txt"
    out = tmp_path / "out.txt"
    inp.write_text("x")
    time.sleep(0.01)
    out.write_text("y")
    assert exists_and_fresh(out, inp) is True               # UT-IO-05
    time.sleep(0.01)
    os.utime(inp, None)                                      # touch input after output
    assert exists_and_fresh(out, inp) is False              # UT-IO-06
    assert exists_and_fresh(tmp_path / "missing", inp) is False


def test_ids_deterministic():  # UT-ID-01
    a = ids.incident_id("demo", "run1.csv", 12.345)
    b = ids.incident_id("demo", "run1.csv", 12.345)
    assert a == b
    assert ids.chunk_id("doc_a", 3) == "doc_a__c0003"


def test_ids_distinct_inputs():  # UT-ID-02
    assert ids.incident_id("demo", "run1.csv", 12.345) != \
        ids.incident_id("demo", "run1.csv", 99.999)
    assert ids.video_id("own", "a.mp4") != ids.video_id("own", "b.mp4")
