"""Patch-token construction for the sensor encoder (decision D13).

Per 12 s sub-window: 95 patches x (RMS + 4 spectral bands) x 3 channels
= a (95, 15) token matrix, flattened to 1425 float32 features. All feature
math imports the one feature path (I-3). Tokens are cached to parquet so
training epochs never re-read waveforms.

Split hygiene (I-4): `load_tokens` NEVER returns test-split windows unless the
caller is scripts/eval_test.py — the loader hard-filters to the requested
splits and refuses 'test'.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.common.config import PipelineConfig
from src.common.io_utils import read_parquet, write_parquet_atomic
from src.features.patching import make_patches
from src.features.vibration import rms, spectral_bands
from src.tgfx.sensor_features import window_signal

N_PATCH_FEATURES = 5          # rms + 4 bands, per channel
TOKENS_FILENAME = "encoder_tokens.parquet"


def patch_tokens_for_window(waveform: pd.DataFrame, t_start: float, t_end: float,
                            fs: float) -> np.ndarray:
    """(n_patches, 15) float32 token matrix for one sub-window."""
    sliced, _signal = window_signal(waveform, t_start, t_end, fs)
    window = sliced[["ax", "ay", "az"]].to_numpy(dtype="float64")
    window = window - np.median(window, axis=0)       # DC offset per channel (D12)
    patches = make_patches(window, fs)                # (n_patches, 3, patch_samples)
    tokens = np.empty((patches.shape[0], patches.shape[1] * N_PATCH_FEATURES),
                      dtype="float32")
    for p in range(patches.shape[0]):
        feats: list[float] = []
        for c in range(patches.shape[1]):
            seg = patches[p, c].tolist()
            feats.append(rms(seg))
            feats.extend(spectral_bands(seg, fs))
        tokens[p] = feats
    return tokens


def tokens_path(cfg: PipelineConfig) -> Path:
    return Path(cfg.paths.data_processed) / TOKENS_FILENAME


def build_token_cache(cfg: PipelineConfig, limit: int | None = None) -> dict:
    """Compute tokens for every carved sub-window and cache them to parquet."""
    subwindows = read_parquet(cfg.paths.subwindows_index)
    sensor_index = read_parquet(cfg.paths.sensor_index)
    incidents = read_parquet(cfg.paths.incidents_index)
    fs_by_incident = dict(zip(sensor_index["incident_id"].astype(str),
                              sensor_index["fs_hz"].astype(float)))
    split_by_incident = dict(zip(incidents["incident_id"].astype(str),
                                 incidents["split"].astype(str)))
    repo_root = Path(cfg.repo_root) if cfg.repo_root else Path.cwd()

    carved = subwindows[subwindows["window_id"].notna()]
    incident_ids = list(dict.fromkeys(carved["incident_id"].astype(str)))
    if limit:
        incident_ids = incident_ids[:limit]

    rows = []
    for incident_id in incident_ids:
        fs = fs_by_incident.get(incident_id)
        split = split_by_incident.get(incident_id, "unknown")
        group = carved[carved["incident_id"] == incident_id].sort_values("t_start")
        if fs is None or group.empty:
            continue
        wf_path = Path(str(group["sensor_file"].iloc[0]))
        if not wf_path.is_absolute():
            wf_path = repo_root / wf_path
        waveform = read_parquet(wf_path)
        for _, sub in group.iterrows():
            tokens = patch_tokens_for_window(
                waveform, float(sub["t_start"]), float(sub["t_end"]), float(fs))
            rows.append({
                "window_id": str(sub["window_id"]),
                "incident_id": incident_id,
                "split": split,
                "n_patches": int(tokens.shape[0]),
                "token_dim": int(tokens.size),
                "tokens": json.dumps(np.round(tokens.flatten(), 6).tolist()),
            })
    frame = pd.DataFrame(rows)
    out = tokens_path(cfg)
    if not frame.empty:
        write_parquet_atomic(frame, out)
    return {"windows": len(frame), "out": out.as_posix(),
            "token_dim": int(frame["token_dim"].iloc[0]) if len(frame) else 0}


def load_tokens(cfg: PipelineConfig, splits: tuple[str, ...]
                ) -> tuple[np.ndarray, pd.DataFrame]:
    """Load cached tokens filtered to *splits*; the test split is refused (I-4)."""
    if "test" in splits:
        raise PermissionError(
            "test-split tokens are quarantined (constitution I-4); "
            "only scripts/eval_test.py may consume test rows")
    frame = read_parquet(tokens_path(cfg))
    frame = frame[frame["split"].isin(splits)].reset_index(drop=True)
    if frame.empty:
        return np.empty((0, 0), dtype="float32"), frame
    x = np.stack([np.asarray(json.loads(t), dtype="float32")
                  for t in frame["tokens"]])
    return x, frame.drop(columns=["tokens"])
