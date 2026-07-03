"""Encoder abstraction — every encoder maps patch tokens to Hvib + anomaly.

Input representation (decision D13): each 12 s sub-window is a token matrix of
shape (n_patches=95, n_features=15) — per patch and channel: RMS + 4 spectral
bands, all computed by the one feature path (I-3). Encoders consume the
flattened float32 matrix. The frozen-VLM rule (I-1) does not apply here: the
sensor encoder is the trainable component of the architecture.

Constitution I-5: anything trainable is seeded; same seed -> same weights,
same Hvib, same anomaly scores.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class SensorEncoder(ABC):
    """Maps (n_windows, token_dim) float32 tokens to embeddings + anomaly scores."""

    dim: int

    @abstractmethod
    def fit(self, tokens: np.ndarray) -> dict:
        """Fit on TRAIN-split tokens only; returns training metrics."""

    @abstractmethod
    def encode(self, tokens: np.ndarray) -> np.ndarray:
        """Return Hvib embeddings, shape (n_windows, self.dim)."""

    @abstractmethod
    def anomaly_scores(self, tokens: np.ndarray) -> np.ndarray:
        """Return anomaly scores in [0, 1], shape (n_windows,)."""


def build_encoder(kind: str, token_dim: int, dim: int = 64, seed: int = 20260702,
                  device: str = "cuda", hidden: int = 256, epochs: int = 20,
                  batch_size: int = 64, lr: float = 1e-3) -> SensorEncoder:
    """Factory keyed by config `encoder.kind`."""
    if kind == "baseline":
        from src.encoder.baseline import BaselineEncoder
        return BaselineEncoder(token_dim=token_dim, dim=dim, seed=seed)
    if kind == "autoencoder":
        from src.encoder.torch_ae import AutoencoderEncoder
        return AutoencoderEncoder(token_dim=token_dim, dim=dim, hidden=hidden,
                                  seed=seed, device=device, epochs=epochs,
                                  batch_size=batch_size, lr=lr)
    raise ValueError(f"unknown encoder kind: {kind}")
