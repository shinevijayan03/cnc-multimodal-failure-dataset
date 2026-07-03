"""Configuration models + loader.

Parse-once -> validate -> pass the typed object explicitly into each stage (no
global singletons, so runs are testable and override-able). See
``docs/software_design.md`` §3.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

from .errors import ConfigError

# Config-schema versions this code understands. Bump on breaking changes.
SUPPORTED_MAJOR_MINOR = {(0, 1)}


# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
class PathsCfg(BaseModel):
    data_raw: str = "data_raw"
    data_processed: str = "data_processed"
    raw_sensor_root: str = "data_raw"
    raw_video_root: str = "data_raw/video_raw"
    raw_text_root: str = "data_raw/text_manuals"
    sensor_windows_dir: str = "data_processed/sensor_windows"
    sensor_index: str = "data_processed/sensor_windows.parquet"
    video_dir: str = "data_processed/video"
    video_index: str = "data_processed/video_index.parquet"
    text_chunks: str = "data_processed/text_chunks.parquet"
    incidents_index: str = "data_processed/incidents.parquet"
    subwindows_index: str = "data_processed/subwindows.parquet"
    sensor_features_index: str = "data_processed/sensor_features.parquet"
    logs_dir: str = "logs"


# --------------------------------------------------------------------------- #
# Sensor
# --------------------------------------------------------------------------- #
class FsEstimationCfg(BaseModel):
    method: str = "median_dt"            # median_dt | metadata | fixed
    min_plausible_hz: float = Field(default=100, gt=0)
    max_plausible_hz: float = Field(default=100_000, gt=0)
    resample_to_hz: float | None = None

    @field_validator("method")
    @classmethod
    def _method_ok(cls, v: str) -> str:
        if v not in {"median_dt", "metadata", "fixed"}:
            raise ValueError(f"fs_estimation.method '{v}' not in median_dt|metadata|fixed")
        return v


class EventDetectionCfg(BaseModel):
    method: str = "rms_threshold"        # rms_threshold | energy_zscore | manual_labels
    channel_for_energy: str = "az"
    window_s: float = Field(default=1.0, gt=0)
    hop_s: float = Field(default=0.25, gt=0)
    threshold_kind: str = "zscore"       # zscore | absolute | quantile
    threshold_value: float = 3.0
    baseline_window_s: float = Field(default=30.0, gt=0)
    min_event_separation_s: float = Field(default=30.0, ge=0)
    min_event_duration_s: float = Field(default=0.5, ge=0)


class WindowingCfg(BaseModel):
    pre_event_s: float = Field(default=60.0, ge=0)
    post_event_s: float = Field(default=30.0, ge=0)
    drop_partial_windows: bool = True
    max_windows_per_run: int | None = None


class EvidenceSpansCfg(BaseModel):
    method: str = "threshold_crossings"  # threshold_crossings | top_k_energy
    pad_s: float = Field(default=1.0, ge=0)
    max_spans: int = Field(default=5, ge=1)


class SensorDatasetCfg(BaseModel):
    name: str
    enabled: bool = True
    path: str
    reader: str
    machine_family: str = "cnc_mill"
    fs_hz: float | None = None
    column_map: dict[str, str] = Field(default_factory=dict)


class SensorCfg(BaseModel):
    datasets: list[SensorDatasetCfg]
    canonical_channels: list[str] = Field(default_factory=lambda: ["time_s", "ax", "ay", "az"])
    optional_channels: list[str] = Field(default_factory=list)
    fs_estimation: FsEstimationCfg = Field(default_factory=FsEstimationCfg)
    event_detection: EventDetectionCfg = Field(default_factory=EventDetectionCfg)
    windowing: WindowingCfg = Field(default_factory=WindowingCfg)
    evidence_spans: EvidenceSpansCfg = Field(default_factory=EvidenceSpansCfg)
    output_format: str = "parquet"
    target_total_incident_hours: float = 72


# --------------------------------------------------------------------------- #
# Video
# --------------------------------------------------------------------------- #
class VideoNormalizeCfg(BaseModel):
    enabled: bool = True
    target_height: int = 720
    target_fps: int = 30
    target_codec: str = "libx264"
    container: str = "mp4"
    clip_min_s: float = 5
    clip_max_s: float = 10
    ffmpeg_path: str = "ffmpeg"
    overwrite: bool = False


class VideoCfg(BaseModel):
    normalize: VideoNormalizeCfg = Field(default_factory=VideoNormalizeCfg)
    regime_labels: list[str] = Field(default_factory=list)
    condition_labels: list[str] = Field(default_factory=list)
    tagging_csv: str = "data_raw/video_raw/video_tags.csv"
    target_clip_count: int = 1000


# --------------------------------------------------------------------------- #
# Text
# --------------------------------------------------------------------------- #
class ChunkingCfg(BaseModel):
    target_tokens: int = Field(default=175, gt=0)
    min_tokens: int = Field(default=80, ge=0)
    max_tokens: int = Field(default=220, gt=0)
    overlap_tokens: int = Field(default=20, ge=0)
    respect_headings: bool = True
    tokenizer: str = "tiktoken_cl100k"   # tiktoken_cl100k | whitespace

    @field_validator("max_tokens")
    @classmethod
    def _max_ge_min(cls, v: int, info: Any) -> int:
        mn = info.data.get("min_tokens")
        if mn is not None and v < mn:
            raise ValueError(f"max_tokens ({v}) < min_tokens ({mn})")
        return v


class TextCfg(BaseModel):
    input_formats: list[str] = Field(default_factory=lambda: ["md", "markdown", "txt", "docx"])
    max_pages_per_doc: int | None = Field(default=None, ge=1)
    dry_run_max_pages_per_doc: int | None = Field(default=2, ge=1)
    chunking: ChunkingCfg = Field(default_factory=ChunkingCfg)
    doc_types: list[str] = Field(default_factory=lambda: ["sop", "maintenance"])
    topic_keywords: dict[str, list[str]] = Field(default_factory=dict)
    target_pages_equivalent: int = 350


# --------------------------------------------------------------------------- #
# Assemble
# --------------------------------------------------------------------------- #
class VideoMatchCfg(BaseModel):
    strategy: str = "label_match"        # label_match | random_within_regime
    require_regime_match: bool = True
    require_condition_match: bool = False
    allow_reuse: bool = True
    fallback_to_idle: bool = True


class TextRetrievalCfg(BaseModel):
    method: str = "keyword_bm25"         # keyword_bm25 | embedding
    sop_chunks_min: int = Field(default=1, ge=0)
    sop_chunks_max: int = Field(default=3, ge=0)
    maintenance_chunks_min: int = Field(default=1, ge=0)
    maintenance_chunks_max: int = Field(default=3, ge=0)
    failure_to_topics: dict[str, list[str]] = Field(default_factory=dict)


class SplitCfg(BaseModel):
    strategy: str = "grouped_by_source"
    fractions: dict[str, float] = Field(
        default_factory=lambda: {"train": 0.7, "val": 0.15, "test": 0.10, "human_eval": 0.05}
    )
    group_key: str = "source_dataset"

    @field_validator("fractions")
    @classmethod
    def _sum_to_one(cls, v: dict[str, float]) -> dict[str, float]:
        total = sum(v.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"split.fractions must sum to 1.0 (got {total})")
        return v


class AssembleCfg(BaseModel):
    video_match: VideoMatchCfg = Field(default_factory=VideoMatchCfg)
    text_retrieval: TextRetrievalCfg = Field(default_factory=TextRetrievalCfg)
    label_fields: list[str] = Field(default_factory=list)
    default_label: str = "unknown"
    split: SplitCfg = Field(default_factory=SplitCfg)


# --------------------------------------------------------------------------- #
# Runtime
# --------------------------------------------------------------------------- #
class RuntimeCfg(BaseModel):
    log_level: str = "INFO"
    log_format: str = "json"             # json | text
    fail_fast: bool = False
    num_workers: int = 1
    dry_run: bool = False


# --------------------------------------------------------------------------- #
# Top-level
# --------------------------------------------------------------------------- #
class PipelineConfig(BaseModel):
    version: str
    random_seed: int = 1337
    paths: PathsCfg
    sensor: SensorCfg
    video: VideoCfg = Field(default_factory=VideoCfg)
    text: TextCfg = Field(default_factory=TextCfg)
    assemble: AssembleCfg = Field(default_factory=AssembleCfg)
    runtime: RuntimeCfg = Field(default_factory=RuntimeCfg)

    # Populated by load_config(); the absolute repo root all relative paths resolve against.
    repo_root: str | None = None

    def resolve(self, p: str | Path) -> Path:
        """Resolve *p* against the repo root (no-op if already absolute)."""
        p = Path(p)
        if p.is_absolute() or self.repo_root is None:
            return p
        return Path(self.repo_root) / p


def _check_version(version: str) -> None:
    try:
        major, minor = (int(x) for x in version.split(".")[:2])
    except (ValueError, AttributeError) as exc:
        raise ConfigError(f"config 'version' is malformed: {version!r}") from exc
    if (major, minor) not in SUPPORTED_MAJOR_MINOR:
        raise ConfigError(
            f"config 'version' {version!r} is unsupported; this code understands "
            f"{sorted(SUPPORTED_MAJOR_MINOR)} (major.minor)"
        )


def load_config(path: str | Path) -> PipelineConfig:
    """Parse YAML, validate into :class:`PipelineConfig`, resolve relative paths
    to absolute against the repo root, and check the schema version.

    Raises :class:`ConfigError` naming the offending key on any failure.
    """
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"config file not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"could not parse YAML in {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"top-level config in {path} must be a mapping")

    if "version" not in raw:
        raise ConfigError("config missing required key 'version'")
    _check_version(str(raw["version"]))

    try:
        cfg = PipelineConfig.model_validate(raw)
    except ValidationError as exc:
        # Re-raise with the offending key(s) named, per the error-handling strategy.
        locs = "; ".join(
            ".".join(str(p) for p in err["loc"]) + f": {err['msg']}"
            for err in exc.errors()
        )
        raise ConfigError(f"invalid config in {path}: {locs}") from exc

    # Repo root = the directory that contains config/ (i.e. config/dataset.yaml -> ../..).
    repo_root = path.resolve().parent.parent
    cfg.repo_root = str(repo_root)
    for field_name in PathsCfg.model_fields:
        rel = getattr(cfg.paths, field_name)
        setattr(cfg.paths, field_name, str(cfg.resolve(rel)))
    return cfg
