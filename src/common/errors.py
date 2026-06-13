"""Custom exception hierarchy for the pipeline.

All pipeline-specific failures subclass :class:`PipelineError` so callers can
catch the whole family with one `except`. See the error-handling strategy in
``docs/software_design.md`` §10.
"""

from __future__ import annotations


class PipelineError(Exception):
    """Base class for all pipeline-specific errors."""


class ConfigError(PipelineError):
    """Raised when configuration is missing, malformed, or out of range.

    The message should name the offending key so the author can fix it fast.
    """


class ReaderError(PipelineError):
    """Raised when a sensor reader cannot parse a raw run."""


class VideoToolError(PipelineError):
    """Raised when ffmpeg/ffprobe is missing or returns a non-zero exit.

    Isolated to the video stage; carries an install hint where relevant.
    """


class AssemblyError(PipelineError):
    """Raised when incident assembly cannot proceed (e.g. missing upstream index)."""
