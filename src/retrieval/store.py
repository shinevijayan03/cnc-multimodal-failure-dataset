"""Local vector store — brute-force cosine over normalized vectors (D14).

At the current corpus scale (934 chunks x 768 dims ≈ 2.7 MB) exact brute-force
search is faster than any index to build and trivially correct; FAISS remains
the documented scale-up path. Persistence is a single parquet file that
records the embedder name so mismatched query embedders are refused.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.common.io_utils import write_parquet_atomic


class VectorStore:
    def __init__(self, dim: int, embedder_name: str):
        self.dim = dim
        self.embedder_name = embedder_name
        self._ids: list[str] = []
        self._vectors: np.ndarray = np.empty((0, dim), dtype="float32")
        self._metadata = pd.DataFrame()

    def __len__(self) -> int:
        return len(self._ids)

    def add(self, ids: list[str], vectors: np.ndarray,
            metadata: pd.DataFrame) -> None:
        vectors = np.asarray(vectors, dtype="float32")
        if vectors.shape != (len(ids), self.dim):
            raise ValueError(f"vectors must be ({len(ids)}, {self.dim}), "
                             f"got {vectors.shape}")
        if len(metadata) != len(ids):
            raise ValueError("metadata rows must match ids")
        if set(ids) & set(self._ids):
            raise ValueError("duplicate ids added to vector store")
        self._ids.extend(str(i) for i in ids)
        self._vectors = np.vstack([self._vectors, vectors])
        self._metadata = pd.concat([self._metadata, metadata.reset_index(drop=True)],
                                   ignore_index=True)

    def search(self, query_vector: np.ndarray, k: int = 5,
               where: dict[str, str] | None = None) -> list[dict]:
        """Top-k cosine hits, optionally filtered by exact metadata matches."""
        if len(self._ids) == 0:
            return []
        query = np.asarray(query_vector, dtype="float32").reshape(-1)
        if query.shape[0] != self.dim:
            raise ValueError(f"query dim {query.shape[0]} != store dim {self.dim}")
        mask = np.ones(len(self._ids), dtype=bool)
        for column, value in (where or {}).items():
            mask &= (self._metadata[column].astype(str) == str(value)).to_numpy()
        candidates = np.flatnonzero(mask)
        if candidates.size == 0:
            return []
        scores = self._vectors[candidates] @ query
        order = np.argsort(scores)[::-1][:k]
        hits = []
        for idx in order:
            row = candidates[idx]
            hits.append({
                "chunk_id": self._ids[row],
                "score": float(scores[idx]),
                **{c: self._metadata.iloc[row][c] for c in self._metadata.columns},
            })
        return hits

    # ------------------------------------------------------------------ persistence
    def save(self, path: str | Path) -> None:
        frame = self._metadata.copy()
        frame.insert(0, "chunk_id_", self._ids)
        frame["vector"] = [json.dumps(np.round(v, 7).tolist()) for v in self._vectors]
        frame.attrs = {}
        meta_row = {"dim": self.dim, "embedder": self.embedder_name,
                    "count": len(self._ids)}
        frame["store_meta"] = json.dumps(meta_row)
        write_parquet_atomic(frame, Path(path))

    @classmethod
    def load(cls, path: str | Path) -> "VectorStore":
        frame = pd.read_parquet(path)
        meta = json.loads(frame["store_meta"].iloc[0])
        store = cls(dim=int(meta["dim"]), embedder_name=str(meta["embedder"]))
        vectors = np.stack([np.asarray(json.loads(v), dtype="float32")
                            for v in frame["vector"]])
        metadata = frame.drop(columns=["chunk_id_", "vector", "store_meta"])
        store.add(list(frame["chunk_id_"].astype(str)), vectors, metadata)
        return store

    def require_embedder(self, embedder_name: str) -> None:
        if embedder_name != self.embedder_name:
            raise ValueError(
                f"store was built with embedder '{self.embedder_name}' but the "
                f"query embedder is '{embedder_name}' — rebuild the index or "
                f"switch embedders (scores across embedders are meaningless)")
