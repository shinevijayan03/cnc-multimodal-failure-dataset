"""Typed data models for every row written to a Parquet index.

Pydantic v2 models with closed enum vocabularies (typos caught at the boundary)
and JSON-list fields stored as JSON strings in Parquet (keeps Arrow flat and
portable while remaining query-able after a one-line decode). See
``docs/software_design.md`` §2.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


# --------------------------------------------------------------------------- #
# Closed label vocabularies
# --------------------------------------------------------------------------- #
class FailureFamily(str, Enum):
    tool_wear = "tool_wear"
    chatter = "chatter"
    clamping_loss = "clamping_loss"
    coolant_fault = "coolant_fault"
    spindle_fault = "spindle_fault"
    unknown = "unknown"


class Regime(str, Enum):
    roughing = "roughing"
    finishing = "finishing"
    plunge = "plunge"
    idle = "idle"
    drilling = "drilling"
    contouring = "contouring"
    unknown = "unknown"


class Condition(str, Enum):
    normal = "normal"
    tool_wear_visible = "tool_wear_visible"
    heavy_vibration = "heavy_vibration"
    coolant_issue = "coolant_issue"
    chatter = "chatter"
    chip_packing = "chip_packing"
    unknown = "unknown"


class DocType(str, Enum):
    sop = "sop"
    maintenance = "maintenance"


class Severity(str, Enum):
    low = "low"
    med = "med"
    high = "high"
    unknown = "unknown"


class Split(str, Enum):
    train = "train"
    val = "val"
    test = "test"
    human_eval = "human_eval"


class AlignmentMethod(str, Enum):
    label_match = "label_match"
    idle_fallback = "idle_fallback"
    none = "none"


# --------------------------------------------------------------------------- #
# Value object
# --------------------------------------------------------------------------- #
class Span(BaseModel):
    """An evidence interval in incident-relative seconds."""

    start_s: float
    end_s: float

    @model_validator(mode="after")
    def _ordered(self) -> "Span":
        if self.end_s < self.start_s:
            raise ValueError(f"end_s ({self.end_s}) < start_s ({self.start_s})")
        return self


# --------------------------------------------------------------------------- #
# Index row models
# --------------------------------------------------------------------------- #
class SensorWindowRow(BaseModel):
    incident_id: str
    source_dataset: str
    machine_family: str
    failure_family: FailureFamily = FailureFamily.unknown
    window_start_s: float            # in original run time
    window_end_s: float
    fs_hz: float
    sensor_file: str                 # path to the per-incident waveform parquet
    sensor_channels: list[str]
    sensor_relevant_spans: list[Span] = Field(default_factory=list)
    n_samples: int | None = None


class VideoIndexRow(BaseModel):
    video_id: str
    video_file: str
    video_fps: float
    duration_s: float
    regime_label: Regime = Regime.unknown
    condition_label: Condition = Condition.unknown
    source: str                      # own | stock | youtube_cc | ...


class TextChunkRow(BaseModel):
    doc_id: str
    chunk_id: str
    doc_type: DocType
    text: str
    topic_tags: list[str] = Field(default_factory=list)
    n_tokens: int


class IncidentRow(BaseModel):
    incident_id: str
    source_dataset: str
    machine_family: str
    failure_family: FailureFamily
    window_start_s: float
    window_end_s: float
    fs_hz: float
    sensor_file: str
    sensor_channels: list[str]
    sensor_relevant_spans: list[Span]
    video_file: str | None = None
    video_fps: float | None = None
    video_relevant_spans: list[Span] = Field(default_factory=list)
    sop_chunk_ids: list[str] = Field(default_factory=list)
    maintenance_chunk_ids: list[str] = Field(default_factory=list)
    phase_label: str = "unknown"
    regime_label: Regime = Regime.unknown
    severity_label: Severity = Severity.unknown
    root_cause_label: str = "unknown"
    alignment_method: AlignmentMethod = AlignmentMethod.none
    split: Split


# Which fields on each row are JSON-list columns in Parquet (serialized as JSON
# strings on write, decoded on read). Used by io_utils at the IO boundary.
JSON_LIST_FIELDS: dict[type[BaseModel], tuple[str, ...]] = {
    SensorWindowRow: ("sensor_channels", "sensor_relevant_spans"),
    VideoIndexRow: (),
    TextChunkRow: ("topic_tags",),
    IncidentRow: (
        "sensor_channels",
        "sensor_relevant_spans",
        "video_relevant_spans",
        "sop_chunk_ids",
        "maintenance_chunk_ids",
    ),
}
