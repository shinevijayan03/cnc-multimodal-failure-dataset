"""Deterministic non-learned baseline encoder.

Hvib = seeded Gaussian random projection of standardized tokens; anomaly =
normalized distance from the train-token mean. No gradients, no torch — the
floor every learned encoder must beat, and the fallback that keeps the
pipeline runnable everywhere.
"""

from __future__ import annotations

import numpy as np

from src.encoder.base import SensorEncoder


class BaselineEncoder(SensorEncoder):
    def __init__(self, token_dim: int, dim: int = 64, seed: int = 20260702):
        self.token_dim = token_dim
        self.dim = dim
        self.seed = seed
        rng = np.random.default_rng(seed)
        self._projection = rng.normal(0.0, 1.0 / np.sqrt(token_dim),
                                      size=(token_dim, dim)).astype("float32")
        self._mean: np.ndarray | None = None
        self._std: np.ndarray | None = None
        self._dist_scale: float | None = None

    def fit(self, tokens: np.ndarray) -> dict:
        self._mean = tokens.mean(axis=0)
        self._std = tokens.std(axis=0)
        self._std[self._std == 0] = 1.0
        dists = np.linalg.norm((tokens - self._mean) / self._std, axis=1)
        self._dist_scale = float(np.quantile(dists, 0.99)) or 1.0
        return {"train_windows": int(len(tokens)),
                "dist_scale_q99": self._dist_scale}

    def _standardize(self, tokens: np.ndarray) -> np.ndarray:
        if self._mean is None:
            raise RuntimeError("BaselineEncoder.fit must run before encode/score")
        return (tokens - self._mean) / self._std

    def encode(self, tokens: np.ndarray) -> np.ndarray:
        return self._standardize(tokens) @ self._projection

    def anomaly_scores(self, tokens: np.ndarray) -> np.ndarray:
        dists = np.linalg.norm(self._standardize(tokens), axis=1)
        return np.clip(dists / self._dist_scale, 0.0, 1.0).astype("float32")
