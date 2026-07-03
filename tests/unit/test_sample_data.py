"""UT-SAMPLE — scripts/generate_sample_data.py fresh-clone bootstrap."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.generate_sample_data import generate


def test_generate_writes_expected_tree(tmp_path: Path):
    summary = generate(tmp_path, seed=123, n_good=2, n_bad=2, no_video=True)
    assert len(summary["sensor_files"]) == 4
    assert len(summary["manual_files"]) == 2
    assert summary["video_status"] == "skipped (--no-video)"
    tags = tmp_path / "video_raw" / "video_tags.csv"
    assert tags.exists()
    for rel in ("sensor_dataset/M01/OP00/good", "sensor_dataset/M01/OP00/bad", "text_manuals"):
        assert (tmp_path / rel).is_dir()


def test_sensor_csv_matches_reader_contract(tmp_path: Path):
    generate(tmp_path, seed=123, n_good=1, n_bad=1, no_video=True)
    csvs = sorted((tmp_path / "sensor_dataset").rglob("*.csv"))
    assert len(csvs) == 2
    df = pd.read_csv(csvs[0])
    assert list(df.columns) == ["x", "y", "z"]           # column_map: x/y/z -> ax/ay/az
    assert len(df) == 40_000                             # 20 s at 2 kHz
    assert df["z"].mean() < -900                         # Bosch-style DC mounting offset


def test_bad_runs_carry_a_burst(tmp_path: Path):
    generate(tmp_path, seed=123, n_good=1, n_bad=1, no_video=True)
    root = tmp_path / "sensor_dataset" / "M01" / "OP00"
    good = pd.read_csv(next((root / "good").glob("*.csv")))
    bad = pd.read_csv(next((root / "bad").glob("*.csv")))
    assert bad["z"].std() > 2 * good["z"].std()


def test_generation_is_deterministic(tmp_path: Path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    generate(a, seed=42, n_good=1, n_bad=1, no_video=True)
    generate(b, seed=42, n_good=1, n_bad=1, no_video=True)
    for rel_a in sorted((a / "sensor_dataset").rglob("*.csv")):
        rel = rel_a.relative_to(a)
        assert rel_a.read_bytes() == (b / rel).read_bytes()
