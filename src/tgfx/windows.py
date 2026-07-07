"""D10 window-convention operationalization (Build Phase 2).

Carves 12-second encoder sub-windows (stride 3 s, per decision D1) from each
incident's available waveform span, computes the default [-12s, 0s] query
window (decision D10), and mints `SW_*` sensor evidence IDs matching the eval
fixture scheme. Where a recording cannot cover a convention, the available
span is used and recorded — never padded (D10).

Pure span math lives in `carve_subwindows` / `resolve_query_window`; the
parquet driver joins them over `sensor_windows.parquet`.

Usage:
    python -m src.tgfx.windows --config config/dataset.yaml [--limit N]
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ..common.config import PipelineConfig, load_config
from ..common.io_utils import read_parquet, write_parquet_atomic

# Incident-relative conventions (docs/_sdd/decisions.md D1 + D10).
INCIDENT_SPAN = (-60.0, 30.0)
SUB_WINDOW_S = 12.0
SUB_WINDOW_STRIDE_S = 3.0
QUERY_WINDOW = (-12.0, 0.0)

_EPS = 1e-9


def sensor_evidence_id(incident_id: str, ordinal: int) -> str:
    """Mint the sensor evidence ID for the *ordinal*-th sub-window.

    Matches the scheme already used by the eval fixtures
    (e.g. ``SW_inc_oracle_001_00`` in src/eval/fixtures.py).
    """
    return f"SW_{incident_id}_{ordinal:02d}"


@dataclass(frozen=True)
class SubWindow:
    """One encoder sub-window, incident-relative seconds."""

    window_id: str
    incident_id: str
    t_start: float
    t_end: float


@dataclass(frozen=True)
class QueryWindowResult:
    """The query window actually available for an incident (D10)."""

    t_start: float
    t_end: float
    requested_start: float
    requested_end: float
    coverage_frac: float          # fraction of the requested window covered
    clipped: bool


def _clip_span(span: tuple[float, float],
               bounds: tuple[float, float] = INCIDENT_SPAN) -> tuple[float, float]:
    lo = max(span[0], bounds[0])
    hi = min(span[1], bounds[1])
    return lo, hi


def carve_subwindows(incident_id: str, available_span: tuple[float, float],
                     duration_s: float = SUB_WINDOW_S,
                     stride_s: float = SUB_WINDOW_STRIDE_S,
                     bounds: tuple[float, float] = INCIDENT_SPAN) -> list[SubWindow]:
    """Return contract-valid sub-windows inside the clipped available span.

    A span shorter than *duration_s* yields no sub-windows (the contract
    requires exactly 12.0 s; D10 forbids synthetic padding) — callers should
    record the short span instead.
    """
    if duration_s <= 0 or stride_s <= 0:
        raise ValueError("duration_s and stride_s must be positive")
    lo, hi = _clip_span(available_span, bounds)
    windows: list[SubWindow] = []
    ordinal = 0
    start = lo
    while start + duration_s <= hi + _EPS:
        windows.append(SubWindow(
            window_id=sensor_evidence_id(incident_id, ordinal),
            incident_id=incident_id,
            t_start=round(start, 6),
            t_end=round(start + duration_s, 6),
        ))
        ordinal += 1
        start = lo + ordinal * stride_s
    return windows


def resolve_query_window(available_span: tuple[float, float],
                         requested: tuple[float, float] = QUERY_WINDOW,
                         bounds: tuple[float, float] = INCIDENT_SPAN) -> QueryWindowResult:
    """Clip the default query window to what the recording actually covers."""
    lo, hi = _clip_span(available_span, bounds)
    q_lo, q_hi = requested
    t_start = max(q_lo, lo)
    t_end = min(q_hi, hi)
    requested_len = q_hi - q_lo
    covered = max(0.0, t_end - t_start)
    if covered <= 0.0:            # no overlap: empty window anchored at the edge
        t_start = t_end = min(max(q_hi, lo), hi)
    return QueryWindowResult(
        t_start=round(t_start, 6),
        t_end=round(t_end, 6),
        requested_start=q_lo,
        requested_end=q_hi,
        coverage_frac=round(covered / requested_len, 6) if requested_len > 0 else 0.0,
        clipped=bool(covered < requested_len - _EPS),
    )


# --------------------------------------------------------------------------- #
# Parquet driver
# --------------------------------------------------------------------------- #
def waveform_span(waveform: pd.DataFrame) -> tuple[float, float]:
    """Available incident-relative span of one per-incident waveform parquet."""
    if "t_rel_s" not in waveform.columns or waveform.empty:
        raise ValueError("waveform parquet must contain a non-empty t_rel_s column")
    return float(waveform["t_rel_s"].min()), float(waveform["t_rel_s"].max())


def build_subwindow_frame(sensor_index: pd.DataFrame, repo_root: Path,
                          limit: int | None = None) -> pd.DataFrame:
    """Carve sub-windows + query windows for every incident in the sensor index."""
    rows: list[dict] = []
    index = sensor_index.head(limit) if limit else sensor_index
    for _, rec in index.iterrows():
        incident = str(rec["incident_id"])
        wf_path = Path(str(rec["sensor_file"]))
        if not wf_path.is_absolute():
            wf_path = repo_root / wf_path
        span = waveform_span(read_parquet(wf_path))
        subwindows = carve_subwindows(incident, span)
        query = resolve_query_window(span)
        base = {
            "incident_id": incident,
            "span_start_s": round(span[0], 6),
            "span_end_s": round(span[1], 6),
            "short_span": len(subwindows) == 0,
            "query_t_start": query.t_start,
            "query_t_end": query.t_end,
            "query_coverage_frac": query.coverage_frac,
            "query_clipped": query.clipped,
            "sensor_file": str(rec["sensor_file"]),
        }
        if not subwindows:        # record the short span itself (D10: no padding)
            rows.append({**base, "window_id": None, "t_start": None, "t_end": None})
        for sw in subwindows:
            rows.append({**base, "window_id": sw.window_id,
                         "t_start": sw.t_start, "t_end": sw.t_end})
    return pd.DataFrame(rows)


def build_subwindow_index(cfg: PipelineConfig, limit: int | None = None,
                          write: bool = True) -> dict:
    """Build (and optionally write) the sub-window index for the configured build."""
    sensor_index = read_parquet(cfg.paths.sensor_index)
    repo_root = Path(cfg.repo_root) if cfg.repo_root else Path.cwd()
    frame = build_subwindow_frame(sensor_index, repo_root, limit=limit)
    out_path = Path(cfg.paths.subwindows_index)
    if write:
        write_parquet_atomic(frame, out_path)
    carved = frame[frame["window_id"].notna()] if not frame.empty else frame
    return {
        "incidents": int(sensor_index.head(limit).shape[0] if limit else len(sensor_index)),
        "subwindows": int(len(carved)),
        "short_span_incidents": int(frame["short_span"].sum()) if not frame.empty else 0,
        "mean_query_coverage": round(float(
            frame.drop_duplicates("incident_id")["query_coverage_frac"].mean()), 4)
        if not frame.empty else 0.0,
        "out": out_path.as_posix() if write else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Carve D10 sub-windows + query windows.")
    parser.add_argument("--config", default="config/dataset.yaml")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--show", type=int, default=0, help="Print the first N carved rows")
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    summary = build_subwindow_index(cfg, limit=args.limit, write=not args.no_write)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if args.show:
        frame = read_parquet(cfg.paths.subwindows_index)
        print(frame.head(args.show).to_string(index=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
