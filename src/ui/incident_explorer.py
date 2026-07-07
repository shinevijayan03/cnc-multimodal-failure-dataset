"""Data-loading helpers for the Streamlit incident explorer.

The UI should stay thin: these helpers understand the generated Parquet
contracts and provide small, testable transformations for display.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.common.io_utils import load_json_col, read_parquet

DEFAULT_PROCESSED_DIR = Path("data_pipeline/data_processed")
INDEX_FILES = {
    "incidents": "incidents.parquet",
    "sensor": "sensor_windows.parquet",
    "text": "text_chunks.parquet",
    "video": "video_index.parquet",
}


@dataclass(frozen=True)
class PipelineTables:
    """Loaded data contract tables used by the UI."""

    processed_dir: Path
    incidents: pd.DataFrame
    text_chunks: pd.DataFrame
    video_index: pd.DataFrame
    sensor_index: pd.DataFrame


def repo_root() -> Path:
    """Return the project root from this module location."""
    return Path(__file__).resolve().parents[2]


def resolve_repo_path(value: Any, root: Path | None = None) -> Path:
    """Resolve a repo-relative artifact path to an absolute path."""
    root = repo_root() if root is None else Path(root)
    path = Path(str(value))
    return path if path.is_absolute() else root / path


def _read_optional_parquet(path: Path) -> pd.DataFrame:
    return read_parquet(path) if path.exists() else pd.DataFrame()


def load_pipeline_tables(processed_dir: str | Path = DEFAULT_PROCESSED_DIR) -> PipelineTables:
    """Load generated Parquet contract tables from *processed_dir*."""
    processed_dir = resolve_repo_path(processed_dir)
    return PipelineTables(
        processed_dir=processed_dir,
        incidents=_read_optional_parquet(processed_dir / INDEX_FILES["incidents"]),
        text_chunks=_read_optional_parquet(processed_dir / INDEX_FILES["text"]),
        video_index=_read_optional_parquet(processed_dir / INDEX_FILES["video"]),
        sensor_index=_read_optional_parquet(processed_dir / INDEX_FILES["sensor"]),
    )


def artifact_status(processed_dir: str | Path = DEFAULT_PROCESSED_DIR) -> pd.DataFrame:
    """Return a compact table showing which generated artifacts are present."""
    processed_dir = resolve_repo_path(processed_dir)
    rows = []
    for label, filename in INDEX_FILES.items():
        path = processed_dir / filename
        rows.append({
            "artifact": label,
            "path": path.as_posix(),
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
        })
    video_dir = processed_dir / "video"
    sensor_dir = processed_dir / "sensor_windows"
    rows.extend([
        {
            "artifact": "normalized_videos",
            "path": video_dir.as_posix(),
            "exists": video_dir.exists(),
            "size_bytes": sum(p.stat().st_size for p in video_dir.glob("*.mp4"))
            if video_dir.exists() else 0,
        },
        {
            "artifact": "sensor_window_files",
            "path": sensor_dir.as_posix(),
            "exists": sensor_dir.exists(),
            "size_bytes": sum(p.stat().st_size for p in sensor_dir.glob("*.parquet"))
            if sensor_dir.exists() else 0,
        },
    ])
    return pd.DataFrame(rows)


def incident_labels(incidents: pd.DataFrame) -> dict[str, str]:
    """Map incident_id -> human-friendly selectbox label."""
    if incidents.empty or "incident_id" not in incidents.columns:
        return {}
    labels: dict[str, str] = {}
    for _, row in incidents.iterrows():
        inc_id = str(row["incident_id"])
        parts = [
            inc_id,
            f"severity={row.get('severity_label', 'unknown')}",
            f"failure={row.get('failure_family', 'unknown')}",
            f"split={row.get('split', 'unknown')}",
        ]
        labels[inc_id] = " | ".join(parts)
    return labels


def find_incident(incidents: pd.DataFrame, incident_id: str) -> pd.Series:
    """Return exactly one incident row by id."""
    matches = incidents[incidents["incident_id"] == incident_id]
    if matches.empty:
        raise KeyError(f"incident not found: {incident_id}")
    return matches.iloc[0]


def decode_list_cell(value: Any) -> list:
    """Decode JSON-list cells from Parquet contracts."""
    return load_json_col(value)


def load_sensor_window(incident: pd.Series, root: Path | None = None) -> tuple[Path, pd.DataFrame]:
    """Load the per-incident sensor waveform referenced by *incident*."""
    sensor_path = resolve_repo_path(incident["sensor_file"], root)
    return sensor_path, read_parquet(sensor_path)


def ordered_chunks(chunks: pd.DataFrame, chunk_ids: list[str]) -> pd.DataFrame:
    """Return chunk rows in the same order as the incident's chunk id list."""
    if chunks.empty or not chunk_ids:
        return pd.DataFrame()
    order = {chunk_id: i for i, chunk_id in enumerate(chunk_ids)}
    out = chunks[chunks["chunk_id"].isin(order)].copy()
    out["_order"] = out["chunk_id"].map(order)
    out = out.sort_values("_order").drop(columns=["_order"])
    return out


def incident_text_evidence(
    incident: pd.Series,
    text_chunks: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return SOP and maintenance chunk rows linked to an incident."""
    sop_ids = [str(x) for x in decode_list_cell(incident.get("sop_chunk_ids"))]
    maint_ids = [str(x) for x in decode_list_cell(incident.get("maintenance_chunk_ids"))]
    return ordered_chunks(text_chunks, sop_ids), ordered_chunks(text_chunks, maint_ids)


def available_sensor_channels(sensor_df: pd.DataFrame) -> list[str]:
    """Return numeric sensor channels appropriate for plotting."""
    excluded = {"time_s", "t_rel_s"}
    return [
        col for col in sensor_df.columns
        if col not in excluded and pd.api.types.is_numeric_dtype(sensor_df[col])
    ]


def downsample_frame(df: pd.DataFrame, max_points: int = 5000) -> pd.DataFrame:
    """Return at most *max_points* rows while preserving the signal shape roughly."""
    if max_points <= 0 or len(df) <= max_points:
        return df
    step = max(1, -(-len(df) // max_points))
    return df.iloc[::step].copy()


def sensor_plot_frame(
    sensor_df: pd.DataFrame,
    channels: list[str],
    max_points: int = 5000,
) -> pd.DataFrame:
    """Prepare a dataframe indexed by relative time for Streamlit line charts."""
    if sensor_df.empty:
        return pd.DataFrame()
    x_col = "t_rel_s" if "t_rel_s" in sensor_df.columns else "time_s"
    cols = [x_col] + [c for c in channels if c in sensor_df.columns]
    frame = downsample_frame(sensor_df[cols], max_points=max_points)
    return frame.set_index(x_col)


def _span_text(spans: list) -> str:
    if not spans:
        return "none"
    pieces = []
    for span in spans:
        if isinstance(span, dict):
            pieces.append(f"{span.get('start_s')}s to {span.get('end_s')}s")
        else:
            pieces.append(str(span))
    return "; ".join(pieces)


def alignment_rows(incident: pd.Series) -> pd.DataFrame:
    """Build a compact alignment summary table for one incident."""
    sensor_spans = decode_list_cell(incident.get("sensor_relevant_spans"))
    video_spans = decode_list_cell(incident.get("video_relevant_spans"))
    sop_ids = decode_list_cell(incident.get("sop_chunk_ids"))
    maint_ids = decode_list_cell(incident.get("maintenance_chunk_ids"))
    return pd.DataFrame([
        {
            "modality": "sensor",
            "artifact": incident.get("sensor_file"),
            "alignment": "anchor window around t_rel_s=0",
            "evidence": _span_text(sensor_spans),
        },
        {
            "modality": "video",
            "artifact": incident.get("video_file"),
            "alignment": incident.get("alignment_method", "unknown"),
            "evidence": _span_text(video_spans),
        },
        {
            "modality": "SOP text",
            "artifact": f"{len(sop_ids)} chunk ids",
            "alignment": "topic retrieval from incident labels",
            "evidence": ", ".join(str(x) for x in sop_ids),
        },
        {
            "modality": "maintenance text",
            "artifact": f"{len(maint_ids)} chunk ids",
            "alignment": "topic retrieval from incident labels",
            "evidence": ", ".join(str(x) for x in maint_ids),
        },
    ])


def video_path_for_display(incident: pd.Series, root: Path | None = None) -> Path | None:
    """Return an absolute video path if the incident has one."""
    video_file = incident.get("video_file")
    if video_file is None or pd.isna(video_file):
        return None
    if str(video_file).strip() == "":
        return None
    return resolve_repo_path(video_file, root)
