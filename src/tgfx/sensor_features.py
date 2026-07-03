"""Sensor sub-window features — Build Phase 3 producer.

Consumes the Phase 2 sub-window index (D10 carving) plus the per-incident
waveforms and emits, per sub-window: RMS, 4-band spectral energy, kurtosis,
variance (all via the ONE feature path, I-3), a heuristic anomaly score, the
important sensor interval, patch geometry (D12), and a sha256 of the raw
window bytes. Contract conformance (`contracts.core.SensorWindow`) is
asserted on a bounded sample of windows per run.

Usage:
    python -m src.tgfx.sensor_features --config config/dataset.yaml [--limit N]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from contracts import SensorWindow
from src.common.config import PipelineConfig, load_config
from src.common.io_utils import read_parquet, write_parquet_atomic
from src.features.patching import DEFAULT_PATCH_S, DEFAULT_STRIDE_S, patch_spec
from src.features.vibration import (
    feature_delta,
    kurtosis,
    rms,
    sliding_rms,
    spectral_bands,
    variance,
)

N_BANDS = 4
IMPORTANT_WINDOW_S = 1.0
IMPORTANT_HOP_S = 0.25


def window_signal(waveform: pd.DataFrame, t_start: float, t_end: float,
                  fs: float) -> tuple[pd.DataFrame, np.ndarray]:
    """Slice one sub-window and build its detrended magnitude signal.

    Slicing is index-based (start via searchsorted, length = duration x fs) so
    float noise in the time column cannot add or drop a sample. The canonical
    per-window signal is the tri-axial magnitude with the median removed
    (DC mounting offset), per decision D12.
    """
    t_rel = waveform["t_rel_s"].to_numpy()
    start_idx = int(np.searchsorted(t_rel, t_start - 0.25 / fs, side="left"))
    n_samples = int(round((t_end - t_start) * fs))
    sliced = waveform.iloc[start_idx:start_idx + n_samples]
    mag = np.sqrt(sliced["ax"].to_numpy() ** 2 + sliced["ay"].to_numpy() ** 2
                  + sliced["az"].to_numpy() ** 2)
    return sliced, mag - float(np.median(mag))


def window_sha256(sliced: pd.DataFrame) -> str:
    digest = hashlib.sha256()
    for channel in ("ax", "ay", "az"):
        digest.update(np.ascontiguousarray(
            sliced[channel].to_numpy(dtype="float64")).tobytes())
    return digest.hexdigest()


def anomaly_score(window_rms: float, baseline_rms: float) -> float:
    """Squash the relative RMS rise into [0, 1); 0 when at/below baseline."""
    delta = feature_delta(window_rms, baseline_rms)
    if delta <= 0.0 or not np.isfinite(delta):
        return 0.0 if delta <= 0.0 else 1.0
    return float(delta / (1.0 + delta))


def important_interval(signal: np.ndarray, fs: float, t_start: float,
                       t_end: float) -> tuple[float, float]:
    """Peak-RMS 1 s interval inside the window (incident-relative seconds)."""
    values, centers = sliding_rms(signal, fs, IMPORTANT_WINDOW_S, IMPORTANT_HOP_S)
    if values.size == 0:
        return t_start, t_end
    peak_center = t_start + float(centers[int(np.argmax(values))])
    half = IMPORTANT_WINDOW_S / 2.0
    return max(t_start, peak_center - half), min(t_end, peak_center + half)


def build_window_row(incident_id: str, window_id: str, t_start: float,
                     t_end: float, fs: float, waveform: pd.DataFrame,
                     baseline_rms: float | None, sensor_file: str) -> dict | None:
    sliced, signal = window_signal(waveform, t_start, t_end, fs)
    if sliced.empty:
        return None
    window_rms = rms(signal.tolist())
    bands = spectral_bands(signal.tolist(), fs, N_BANDS)
    imp_lo, imp_hi = important_interval(signal, fs, t_start, t_end)
    spec = patch_spec(len(sliced), 3, fs)
    return {
        "window_id": window_id,
        "incident_id": incident_id,
        "t_start": t_start,
        "t_end": t_end,
        "sample_rate_hz": fs,
        "n_samples": int(len(sliced)),
        "rms": window_rms,
        "spec_band_0": bands[0], "spec_band_1": bands[1],
        "spec_band_2": bands[2], "spec_band_3": bands[3],
        "kurtosis": kurtosis(signal.tolist()),
        "variance": variance(signal.tolist()),
        "anomaly_score": anomaly_score(window_rms, baseline_rms)
        if baseline_rms is not None else 0.0,
        "important_start_s": imp_lo,
        "important_end_s": imp_hi,
        "n_patches": spec.n_patches,
        "patch_samples": spec.patch_samples,
        "patch_s": DEFAULT_PATCH_S,
        "stride_s": DEFAULT_STRIDE_S,
        "sha256": window_sha256(sliced),
        "sensor_file": sensor_file,
    }


def validate_contract_sample(rows: list[dict], waveforms: dict[str, pd.DataFrame],
                             n: int = 5) -> int:
    """Assert full `SensorWindow` contract conformance on the first *n* rows."""
    validated = 0
    for row in rows[:n]:
        waveform = waveforms.get(row["incident_id"])
        if waveform is None:
            continue
        sliced, _ = window_signal(waveform, row["t_start"], row["t_end"],
                                  row["sample_rate_hz"])
        SensorWindow(
            window_id=row["window_id"],
            incident_id=row["incident_id"],
            t_start=row["t_start"],
            t_end=row["t_end"],
            sample_rate_hz=row["sample_rate_hz"],
            channels={c: sliced[c].tolist() for c in ("ax", "ay", "az")},
            rms=row["rms"],
            spectral_energy=[row["spec_band_0"], row["spec_band_1"],
                             row["spec_band_2"], row["spec_band_3"]],
            kurtosis=row["kurtosis"],
            variance=row["variance"],
            source_file=row["sensor_file"],
            sha256=row["sha256"],
        )
        validated += 1
    return validated


def build_sensor_features(cfg: PipelineConfig, limit: int | None = None,
                          write: bool = True, validate_n: int = 5) -> dict:
    subwindows = read_parquet(cfg.paths.subwindows_index)
    sensor_index = read_parquet(cfg.paths.sensor_index)
    fs_by_incident = dict(zip(sensor_index["incident_id"].astype(str),
                              sensor_index["fs_hz"].astype(float)))
    repo_root = Path(cfg.repo_root) if cfg.repo_root else Path.cwd()

    carved = subwindows[subwindows["window_id"].notna()]
    incident_ids = list(dict.fromkeys(carved["incident_id"].astype(str)))
    if limit:
        incident_ids = incident_ids[:limit]

    rows: list[dict] = []
    waveforms: dict[str, pd.DataFrame] = {}
    skipped = 0
    for incident_id in incident_ids:
        group = carved[carved["incident_id"] == incident_id].sort_values("t_start")
        fs = fs_by_incident.get(incident_id)
        if fs is None or group.empty:
            skipped += 1
            continue
        wf_path = Path(str(group["sensor_file"].iloc[0]))
        if not wf_path.is_absolute():
            wf_path = repo_root / wf_path
        waveform = read_parquet(wf_path)
        if len(waveforms) < max(validate_n, 1):
            waveforms[incident_id] = waveform

        baseline_rms: float | None = None
        for _, sub in group.iterrows():
            row = build_window_row(
                incident_id, str(sub["window_id"]), float(sub["t_start"]),
                float(sub["t_end"]), float(fs), waveform, baseline_rms,
                str(sub["sensor_file"]))
            if row is None:
                skipped += 1
                continue
            if baseline_rms is None:      # earliest window anchors the baseline
                baseline_rms = row["rms"]
                row["anomaly_score"] = 0.0
            rows.append(row)

    validated = validate_contract_sample(rows, waveforms, n=validate_n)
    frame = pd.DataFrame(rows)
    out_path = Path(cfg.paths.sensor_features_index)
    if write and not frame.empty:
        write_parquet_atomic(frame, out_path)
    return {
        "incidents": len(incident_ids),
        "windows": int(len(frame)),
        "skipped": skipped,
        "contract_validated": validated,
        "mean_anomaly_score": round(float(frame["anomaly_score"].mean()), 4)
        if not frame.empty else 0.0,
        "out": out_path.as_posix() if write else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Phase 3 sensor features.")
    parser.add_argument("--config", default="config/dataset.yaml")
    parser.add_argument("--limit", type=int, default=None, help="Max incidents")
    parser.add_argument("--validate", type=int, default=5,
                        help="Contract-validate the first N windows")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    summary = build_sensor_features(cfg, limit=args.limit, write=not args.no_write,
                                    validate_n=args.validate)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
