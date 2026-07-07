"""Trainable autoencoder encoder (Build Phase 4).

MLP autoencoder over the flattened D13 token matrix: token_dim -> hidden ->
dim (Hvib bottleneck) -> hidden -> token_dim, MSE loss. Anomaly score is the
per-window reconstruction error normalized by the train-error distribution —
windows the model cannot reconstruct look unlike the training regime.

Device policy (decision D11): the local GPU is used whenever available;
requesting "cuda" without one raises with a clear message instead of silently
falling back. Tests pass device="cpu" explicitly (test-only escape hatch).

Determinism (I-5): torch + numpy seeded from --seed; same seed -> same
weights -> same Hvib and scores (deterministic algorithms enforced).
"""

from __future__ import annotations

import os

import numpy as np

from src.encoder.base import SensorEncoder

# cuBLAS needs this set before its first call for deterministic GPU matmuls
# (I-5 determinism on CUDA >= 10.2). Harmless on CPU. Found on the RTX 3060
# during Phase 4 bring-up; see docs/runbook.md GPU section.
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")


class AutoencoderEncoder(SensorEncoder):
    def __init__(self, token_dim: int, dim: int = 64, hidden: int = 256,
                 seed: int = 20260702, device: str = "cuda", epochs: int = 20,
                 batch_size: int = 64, lr: float = 1e-3):
        import torch
        from torch import nn

        self.torch = torch
        self.token_dim = token_dim
        self.dim = dim
        self.seed = seed
        self.epochs = epochs
        self.batch_size = batch_size
        self.lr = lr

        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError(
                "encoder.device='cuda' but no CUDA device is available. "
                "Per decision D11 the GPU is required; pass device='cpu' only "
                "in tests.")
        self.device = torch.device(device)

        torch.manual_seed(seed)
        np.random.seed(seed % (2 ** 32))
        torch.use_deterministic_algorithms(True)

        self.model = nn.Sequential(
            nn.Linear(token_dim, hidden), nn.ReLU(),
            nn.Linear(hidden, dim),                      # Hvib bottleneck
            nn.ReLU(),
            nn.Linear(dim, hidden), nn.ReLU(),
            nn.Linear(hidden, token_dim),
        ).to(self.device)
        self._encoder_slice = self.model[:3]
        self._mean: np.ndarray | None = None
        self._std: np.ndarray | None = None
        self._err_scale: float | None = None

    # ------------------------------------------------------------------ helpers
    def _standardize(self, tokens: np.ndarray) -> np.ndarray:
        if self._mean is None:
            raise RuntimeError("AutoencoderEncoder.fit must run before encode/score")
        return ((tokens - self._mean) / self._std).astype("float32")

    def _recon_errors(self, tokens: np.ndarray) -> np.ndarray:
        torch = self.torch
        x = torch.from_numpy(self._standardize(tokens)).to(self.device)
        self.model.eval()
        errors = []
        with torch.no_grad():
            for i in range(0, len(x), self.batch_size):
                batch = x[i:i + self.batch_size]
                recon = self.model(batch)
                errors.append(((recon - batch) ** 2).mean(dim=1).cpu().numpy())
        return np.concatenate(errors) if errors else np.empty(0)

    # ------------------------------------------------------------------ API
    def fit(self, tokens: np.ndarray) -> dict:
        torch = self.torch
        self._mean = tokens.mean(axis=0)
        self._std = tokens.std(axis=0)
        self._std[self._std == 0] = 1.0

        x = torch.from_numpy(self._standardize(tokens)).to(self.device)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.lr)
        loss_fn = torch.nn.MSELoss()
        generator = torch.Generator().manual_seed(self.seed)

        self.model.train()
        first_loss = last_loss = float("nan")
        for epoch in range(self.epochs):
            perm = torch.randperm(len(x), generator=generator)
            epoch_losses = []
            for i in range(0, len(x), self.batch_size):
                batch = x[perm[i:i + self.batch_size]]
                optimizer.zero_grad()
                loss = loss_fn(self.model(batch), batch)
                loss.backward()
                optimizer.step()
                epoch_losses.append(float(loss.detach().cpu()))
            last_loss = float(np.mean(epoch_losses))
            if epoch == 0:
                first_loss = last_loss

        train_errors = self._recon_errors(tokens)
        self._err_scale = float(np.quantile(train_errors, 0.99)) or 1.0
        return {
            "train_windows": int(len(tokens)),
            "epochs": self.epochs,
            "first_epoch_loss": round(first_loss, 6),
            "final_epoch_loss": round(last_loss, 6),
            "train_recon_mse_mean": round(float(train_errors.mean()), 6),
            "err_scale_q99": round(self._err_scale, 6),
            "device": str(self.device),
        }

    def encode(self, tokens: np.ndarray) -> np.ndarray:
        torch = self.torch
        x = torch.from_numpy(self._standardize(tokens)).to(self.device)
        self.model.eval()
        outs = []
        with torch.no_grad():
            for i in range(0, len(x), self.batch_size):
                outs.append(self._encoder_slice(x[i:i + self.batch_size]).cpu().numpy())
        return np.concatenate(outs) if outs else np.empty((0, self.dim))

    def anomaly_scores(self, tokens: np.ndarray) -> np.ndarray:
        errors = self._recon_errors(tokens)
        return np.clip(errors / self._err_scale, 0.0, 1.0).astype("float32")

    def save(self, path) -> None:
        self.torch.save({
            "state_dict": self.model.state_dict(),
            "mean": self._mean, "std": self._std, "err_scale": self._err_scale,
            "token_dim": self.token_dim, "dim": self.dim, "seed": self.seed,
        }, path)
