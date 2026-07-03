"""Core TGFX data contracts.

Source: C:/Users/Admin/Downloads/master_prompt.md, section 3.
These contracts are additive; they do not alter the existing Recipe A Parquet
contracts in `src.common.schemas`.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SubCause(str, Enum):
    """Five-class abnormal-vibration sub-cause taxonomy from decision D6."""

    IMBALANCE = "imbalance"
    MISALIGNMENT = "misalignment"
    BEARING_WEAR = "bearing_wear"
    LOOSENESS = "mechanical_looseness"
    TOOL_WEAR = "tool_wear_progression"


class WindowPhase(str, Enum):
    NORMAL = "normal"
    PRE_FAILURE = "pre_failure"
    FAILURE = "failure"
    POST_ALARM = "post_alarm"


class SensorWindow(BaseModel):
    """A 12-second sensor sub-window inside the [-60s, +30s] incident span."""

    window_id: str
    incident_id: str
    t_start: float
    t_end: float
    sample_rate_hz: float = Field(gt=0)
    channels: dict[str, list[float]]
    rms: float
    spectral_energy: list[float] = Field(min_length=4, max_length=4)
    kurtosis: float
    variance: float
    phase_label: WindowPhase | None = None
    source_file: str
    sha256: str

    @model_validator(mode="after")
    def _validate_window(self) -> "SensorWindow":
        if not (-60.0 <= self.t_start < self.t_end <= 30.0):
            raise ValueError("sensor window must fit inside [-60.0, +30.0]")
        if abs((self.t_end - self.t_start) - 12.0) >= 1e-6:
            raise ValueError("sensor sub-window duration must be 12.0 seconds")
        if set(self.channels) != {"ax", "ay", "az"}:
            raise ValueError("sensor channels must be exactly ax, ay, az")
        return self


class VideoClip(BaseModel):
    """A video clip aligned to an incident, with explicit sync provenance."""

    clip_id: str
    incident_id: str
    t_start: float
    t_end: float
    fps: int = Field(gt=0)
    frame_range: tuple[int, int]
    clip_uri: str
    sync_provenance: Literal["measured", "constructed"]
    clip_summary: str | None = None
    visual_labels: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_clip(self) -> "VideoClip":
        if self.t_end <= self.t_start:
            raise ValueError("video clip end must be after start")
        if self.frame_range[1] < self.frame_range[0]:
            raise ValueError("frame_range end must be >= start")
        return self


class SOPChunk(BaseModel):
    chunk_id: str
    doc_id: str
    section_ref: str
    text: str
    tags: dict[str, str] = Field(default_factory=dict)
    embedding_model: str = "BAAI/bge-base-en-v1.5"
    embedding_dim: int = 768


class TimelineEntry(BaseModel):
    t_start_sec: float
    t_end_sec: float
    sensor_evidence: str | None = None
    video_evidence: str | None = None
    sop_evidence: str | None = None

    @model_validator(mode="after")
    def _ordered(self) -> "TimelineEntry":
        if self.t_end_sec < self.t_start_sec:
            raise ValueError("timeline entry end must be >= start")
        return self


class IncidentTuple(BaseModel):
    incident_id: str
    equipment_id: str
    machine_family: str
    failure_family: str
    sub_cause_gold: SubCause | None = None
    alarm_time: str
    sensor_windows: list[str]
    video_clips: list[str]
    sop_chunks: list[str]
    timeline: list[TimelineEntry]
    split: Literal["train", "val", "test"]


class AlignedTuple(BaseModel):
    window_id: str
    sensor_summary: str
    clip_summary: str
    retrieved_text: str
    alarm_state: str
    mode_state: str
    timestamp_span: tuple[float, float]
    evidence_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _ordered_span(self) -> "AlignedTuple":
        if self.timestamp_span[1] < self.timestamp_span[0]:
            raise ValueError("timestamp span end must be >= start")
        return self
