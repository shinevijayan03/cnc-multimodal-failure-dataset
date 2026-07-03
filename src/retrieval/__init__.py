"""Retrieval package (Build Phase 5) — SOP embeddings + vector store."""

from src.retrieval.embeddings import build_embedder
from src.retrieval.store import VectorStore

__all__ = ["build_embedder", "VectorStore"]
