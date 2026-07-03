"""Embedding interfaces for SOP/maintenance chunks (Build Phase 5).

Primary: BAAI/bge-base-en-v1.5 (768-d), exactly what the `SOPChunk` contract
declares, running on the local GPU (decision D11). Fallback: a deterministic
hashing embedder for tests and model-less environments — always clearly named
`hashing_fallback` so no store built with it can masquerade as BGE (the store
records its embedder name and search refuses mismatched embedders).

All embedders return L2-normalized float32 vectors, so cosine similarity is a
plain dot product.
"""

from __future__ import annotations

import hashlib
import re

import numpy as np

BGE_MODEL = "BAAI/bge-base-en-v1.5"
BGE_DIM = 768
# BGE recommends a query instruction for short retrieval queries.
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class HashingEmbedder:
    """Deterministic token-hashing embedder (fallback / tests only)."""

    def __init__(self, dim: int = BGE_DIM, seed: int = 20260702):
        self.dim = dim
        self.name = "hashing_fallback"
        self._seed = seed

    def _token_vector(self, token: str) -> np.ndarray:
        digest = hashlib.sha256(f"{self._seed}:{token}".encode("utf-8")).digest()
        rng = np.random.default_rng(int.from_bytes(digest[:8], "little"))
        return rng.normal(0.0, 1.0, self.dim).astype("float32")

    def embed(self, texts: list[str], queries: bool = False) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype="float32")
        for i, text in enumerate(texts):
            tokens = re.findall(r"[a-z0-9]+", text.lower())
            for token in tokens:
                out[i] += self._token_vector(token)
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return out / norms


class BgeEmbedder:
    """BGE-base-en-v1.5 via sentence-transformers on the local GPU (D11)."""

    def __init__(self, model_name: str = BGE_MODEL, device: str = "cuda",
                 batch_size: int = 32):
        import torch
        from sentence_transformers import SentenceTransformer

        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError(
                "retrieval.device='cuda' but no CUDA device is available "
                "(decision D11: the local GPU is required; 'cpu' is test-only)")
        self.name = model_name
        self.dim = BGE_DIM
        self.batch_size = batch_size
        self._model = SentenceTransformer(model_name, device=device)

    def embed(self, texts: list[str], queries: bool = False) -> np.ndarray:
        if queries:
            texts = [BGE_QUERY_PREFIX + t for t in texts]
        vectors = self._model.encode(
            texts, batch_size=self.batch_size, normalize_embeddings=True,
            convert_to_numpy=True, show_progress_bar=False)
        return np.asarray(vectors, dtype="float32")


def build_embedder(kind: str, model_name: str = BGE_MODEL, device: str = "cuda",
                   batch_size: int = 32, dim: int = BGE_DIM, seed: int = 20260702):
    if kind == "bge":
        return BgeEmbedder(model_name=model_name, device=device,
                           batch_size=batch_size)
    if kind == "hashing":
        return HashingEmbedder(dim=dim, seed=seed)
    raise ValueError(f"unknown embedder kind: {kind}")
