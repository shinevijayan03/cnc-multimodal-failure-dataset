"""UT-VIS7 — Build Phase 7 vision package (summarizers, builder, UI events)."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from src.vision.summarizer import TagSummarizer, parse_vlm_json
from src.ui.workbench import video_summary_for, vlm_video_events


# ------------------------------------------------------------------ parser
def test_parse_vlm_json_happy_path():
    text = ('Sure! {"summary": "Steady cut with visible coolant.", '
            '"labels": ["normal_cut", "coolant_flow"], "confidence": 0.85}')
    summary, labels, conf = parse_vlm_json(text)
    assert summary == "Steady cut with visible coolant."
    assert labels == ["normal_cut", "coolant_flow"] and conf == 0.85


def test_parse_vlm_json_clamps_and_limits():
    text = '{"summary": "s", "labels": ["a","b","c","d","e"], "confidence": 7}'
    _s, labels, conf = parse_vlm_json(text)
    assert len(labels) == 4 and conf == 1.0


def test_parse_vlm_json_nonjson_falls_back_low_confidence():
    summary, labels, conf = parse_vlm_json("The spindle appears to rotate.")
    assert summary.startswith("The spindle") and labels == [] and conf == 0.3


# ------------------------------------------------------------------ tags fallback
def test_tag_summarizer_uses_real_tags_and_is_deterministic():
    s = TagSummarizer()
    a = s.summarize("v.mp4", regime="roughing", condition="heavy_vibration")
    b = s.summarize("v.mp4", regime="roughing", condition="heavy_vibration")
    assert a == b
    assert a.mode == "tags_only" and a.model == "video_tags.csv"
    assert a.visual_labels == ["roughing", "heavy_vibration"]
    assert "no VLM" in a.summary                      # can't masquerade as VLM


# ------------------------------------------------------------------ builder (tags mode)
def test_build_video_summaries_tags_mode(tmp_path):
    from src.common.config import load_config
    from src.vision.build_summaries import build_video_summaries
    from tests.conftest import MINI_YAML

    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "dataset.yaml").write_text(MINI_YAML, encoding="utf-8")
    cfg = load_config(tmp_path / "config" / "dataset.yaml")
    index = pd.DataFrame([
        {"video_id": "vid_000", "video_file": "data_processed/video/a.mp4",
         "video_fps": 30.0, "duration_s": 7.0, "regime_label": "roughing",
         "condition_label": "chatter", "source": "own"},
    ])
    from src.common.io_utils import write_parquet_atomic
    write_parquet_atomic(index, cfg.paths.video_index)
    summary = build_video_summaries(cfg, mode="tags_only")
    assert summary["clips"] == 1 and summary["mode_counts"] == {"tags_only": 1}
    frame = pd.read_parquet(f"{cfg.paths.data_processed}/video_summaries.parquet")
    assert json.loads(frame.iloc[0]["visual_labels"]) == ["roughing", "chatter"]


# ------------------------------------------------------------------ grounding + contract
def test_videoclip_contract_sample_validates():
    from src.temporal.grounding import _validate_videoclip
    incident = pd.Series({"incident_id": "inc_a", "video_fps": 30.0})
    features = pd.DataFrame([{"t_start": -8.0, "t_end": 4.0},
                             {"t_start": -5.0, "t_end": 7.0}])
    row = pd.Series({"video_id": "vid_000", "video_file": "v.mp4",
                     "summary": "steady cut", "visual_labels": json.dumps(["normal"])})
    _validate_videoclip(incident, features, row)      # pydantic accepts

    bad = pd.Series({"video_id": "vid_000", "video_file": "v.mp4",
                     "summary": "s", "visual_labels": json.dumps([])})
    features_bad = pd.DataFrame([{"t_start": 4.0, "t_end": -8.0}])  # end < start
    with pytest.raises(Exception):
        _validate_videoclip(incident, features_bad, bad)


# ------------------------------------------------------------------ UI events
def test_vlm_video_events_replace_demo_and_carry_provenance():
    summaries = pd.DataFrame([{
        "video_id": "vid_000", "video_file": "v.mp4",
        "summary": "Oscillatory shaft motion with chatter marks.",
        "visual_labels": json.dumps(["chatter_marks", "vibration_blur"]),
        "confidence": 0.82, "model": "Qwen/Qwen2.5-VL-3B-Instruct", "mode": "vlm",
        "frames_used": 8,
    }])
    summary = video_summary_for(summaries, "v.mp4")
    assert summary is not None and summary["mode"] == "vlm"
    events = vlm_video_events(summary, 0.0, 16.0)
    assert len(events) == 1 and events[0].row == "VIDEO"
    assert events[0].source == "grounded"
    assert "VLM: chatter_marks" in events[0].label
    assert "constructed" in events[0].detail          # I-8 caveat travels
    assert video_summary_for(summaries, "other.mp4") is None
