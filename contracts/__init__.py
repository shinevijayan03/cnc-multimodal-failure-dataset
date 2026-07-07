"""TGFX contract package.

These Pydantic models are the spec-defined inter-agent API for the TGFX build.
They intentionally live beside the existing Recipe A `src.common.schemas`
models instead of replacing them.
"""

from .core import (
    AlignedTuple,
    IncidentTuple,
    SOPChunk,
    SensorWindow,
    SubCause,
    TimelineEntry,
    VideoClip,
    WindowPhase,
)
from .explanation import ChainClaim, ExplanationOutput

__all__ = [
    "AlignedTuple",
    "ChainClaim",
    "ExplanationOutput",
    "IncidentTuple",
    "SOPChunk",
    "SensorWindow",
    "SubCause",
    "TimelineEntry",
    "VideoClip",
    "WindowPhase",
]
