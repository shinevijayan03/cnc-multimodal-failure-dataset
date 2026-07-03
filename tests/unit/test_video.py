"""Video ETL tests — UT-VID-01..07 (subprocess mocked)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from src.common.config import VideoNormalizeCfg
from src.common.errors import VideoToolError
from src.common.io_utils import read_parquet
from src.etl.video_etl import FfmpegNormalizer, TagMerger, VideoETL, parse_probe

PROBE_JSON = """
{"streams": [{"codec_type": "video", "codec_name": "h264",
  "avg_frame_rate": "30/1", "r_frame_rate": "30/1", "width": 1280, "height": 720,
  "duration": "7.5"}], "format": {"duration": "7.5"}}
"""


def test_probe_parse():  # UT-VID-01
    info = parse_probe(PROBE_JSON)
    assert info["fps"] == 30.0
    assert info["duration_s"] == 7.5
    assert info["codec"] == "h264"
    assert info["height"] == 720 and info["width"] == 1280


def test_ffmpeg_arg_vector():  # UT-VID-02
    cfg = VideoNormalizeCfg(target_height=720, target_fps=30, target_codec="libx264")
    args = FfmpegNormalizer(cfg).build_command(Path("in.mp4"), Path("out.mp4"))
    joined = " ".join(args)
    assert "720" in joined and "fps=30" in joined and "libx264" in joined
    assert args[-1].endswith(".mp4")


def test_skip_conformant(tmp_path, monkeypatch):  # UT-VID-03
    called = {"ffmpeg": False}

    def spy(*a, **k):
        called["ffmpeg"] = True
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", spy)
    src = tmp_path / "in.mp4"
    src.write_bytes(b"x")
    cfg = VideoNormalizeCfg(target_height=720, target_fps=30)
    conformant = {"height": 720, "fps": 30.0, "codec": "h264", "duration_s": 7.0}
    info = FfmpegNormalizer(cfg).normalize(src, tmp_path / "out.mp4", info=conformant)
    assert called["ffmpeg"] is False                        # no ffmpeg call
    assert (tmp_path / "out.mp4").exists()
    assert info["height"] == 720


def test_ffmpeg_failure_handled(tmp_path, monkeypatch):  # UT-VID-04
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: SimpleNamespace(returncode=1, stdout="", stderr="boom"))
    src = tmp_path / "in.mp4"
    src.write_bytes(b"x")
    nonconf = {"height": 480, "fps": 25.0, "codec": "mpeg4", "duration_s": 7.0}
    with pytest.raises(VideoToolError):
        FfmpegNormalizer(VideoNormalizeCfg()).normalize(src, tmp_path / "out.mp4", info=nonconf)


def test_ffmpeg_missing_handled(tmp_path, monkeypatch):  # UT-VID-05
    def missing(*a, **k):
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr(subprocess, "run", missing)
    src = tmp_path / "in.mp4"
    src.write_bytes(b"x")
    nonconf = {"height": 480, "fps": 25.0, "codec": "mpeg4", "duration_s": 7.0}
    with pytest.raises(VideoToolError) as exc:
        FfmpegNormalizer(VideoNormalizeCfg()).normalize(src, tmp_path / "out.mp4", info=nonconf)
    assert "ffmpeg" in str(exc.value).lower()


def test_tag_merge_present():  # UT-VID-06
    df = pd.DataFrame([{"video_file": "clip01.mp4", "regime": "roughing",
                        "condition": "tool_wear_visible", "source": "own"}])
    regime, condition, source = TagMerger(df).merge(["clip01.mp4"])
    assert regime.value == "roughing"
    assert condition.value == "tool_wear_visible"
    assert source == "own"


def test_tag_merge_absent():  # UT-VID-07
    df = pd.DataFrame([{"video_file": "clip01.mp4", "regime": "roughing"}])
    regime, condition, source = TagMerger(df).merge(["other.mp4"])
    assert regime.value == "unknown" and condition.value == "unknown" and source == "unknown"


def test_video_etl_indexes_raw_when_ffmpeg_missing(mini_cfg, monkeypatch):  # UT-VID-08
    raw = Path(mini_cfg.paths.raw_video_root)
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "clip.mov").write_bytes(b"not a real movie, but enough for discovery")
    monkeypatch.setattr(VideoETL, "_tools_available", lambda self: False)

    summ = VideoETL(mini_cfg).run()

    assert summ.written == 1
    assert summ.notes["reason"] == "ffmpeg_missing_raw_index"
    idx = read_parquet(mini_cfg.paths.video_index)
    assert len(idx) == 1
    assert idx.iloc[0]["video_file"].endswith("clip.mov")
