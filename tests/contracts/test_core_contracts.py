from __future__ import annotations

import pytest
from pydantic import ValidationError

from contracts import SensorWindow, SubCause, VideoClip


def _sensor_window(**overrides):
    data = {
        "window_id": "SW_inc_001_00",
        "incident_id": "inc_001",
        "t_start": -60.0,
        "t_end": -48.0,
        "sample_rate_hz": 2000.0,
        "channels": {"ax": [0.0], "ay": [0.1], "az": [0.2]},
        "rms": 0.2,
        "spectral_energy": [0.1, 0.2, 0.3, 0.4],
        "kurtosis": 3.1,
        "variance": 0.02,
        "source_file": "data/raw/inc_001.csv",
        "sha256": "abc123",
    }
    data.update(overrides)
    return SensorWindow(**data)


def test_sensor_window_accepts_spec_span_and_channels():
    window = _sensor_window()
    assert window.t_end - window.t_start == 12.0
    assert set(window.channels) == {"ax", "ay", "az"}


def test_sensor_window_rejects_non_12_second_span():
    with pytest.raises(ValidationError, match="12.0 seconds"):
        _sensor_window(t_end=-47.0)


def test_sensor_window_rejects_non_canonical_channels():
    with pytest.raises(ValidationError, match="ax, ay, az"):
        _sensor_window(channels={"vibration_x": [0.0], "ay": [0.1], "az": [0.2]})


def test_video_clip_requires_explicit_sync_provenance():
    with pytest.raises(ValidationError):
        VideoClip(
            clip_id="VC_inc_001_00",
            incident_id="inc_001",
            t_start=-10.0,
            t_end=0.0,
            fps=30,
            frame_range=(0, 300),
            clip_uri="data/raw/video.mp4",
        )


def test_subcause_taxonomy_contains_five_classes():
    assert {item.value for item in SubCause} == {
        "imbalance",
        "misalignment",
        "bearing_wear",
        "mechanical_looseness",
        "tool_wear_progression",
    }
