"""UT-RET5 — Build Phase 5 retrieval package (embeddings, store, index build)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from src.retrieval.build_index import (
    chunk_metadata,
    citation_for,
    validate_contract_sample,
)
from src.retrieval.embeddings import HashingEmbedder, build_embedder
from src.retrieval.store import VectorStore

DIM = 64


def _store_with(vectors: np.ndarray, ids: list[str],
                doc_types: list[str]) -> VectorStore:
    store = VectorStore(dim=vectors.shape[1], embedder_name="hashing_fallback")
    store.add(ids, vectors, pd.DataFrame({
        "doc_type": doc_types,
        "citation": [f"{t}:doc§{i}" for i, t in zip(ids, doc_types)],
        "text": [f"text {i}" for i in ids],
    }))
    return store


# ------------------------------------------------------------------ embedders
def test_hashing_embedder_deterministic_and_normalized():
    a = HashingEmbedder(dim=DIM, seed=1)
    b = HashingEmbedder(dim=DIM, seed=1)
    texts = ["bearing vibration threshold", "coolant flow check"]
    va, vb = a.embed(texts), b.embed(texts)
    np.testing.assert_array_equal(va, vb)
    np.testing.assert_allclose(np.linalg.norm(va, axis=1), 1.0, rtol=1e-5)
    assert va.shape == (2, DIM)


def test_hashing_embedder_similarity_reflects_token_overlap():
    emb = HashingEmbedder(dim=256, seed=1)
    v = emb.embed(["bearing vibration rms", "bearing vibration energy",
                   "coolant lubricant flood"])
    sim_close = float(v[0] @ v[1])
    sim_far = float(v[0] @ v[2])
    assert sim_close > sim_far


def test_build_embedder_rejects_unknown_kind():
    with pytest.raises(ValueError):
        build_embedder("word2vec")


# ------------------------------------------------------------------ store
def test_store_search_ranks_by_cosine():
    base = np.eye(3, DIM, dtype="float32")           # 3 orthonormal vectors
    store = _store_with(base, ["a", "b", "c"], ["sop", "sop", "maintenance"])
    hits = store.search(base[1], k=2)
    assert hits[0]["chunk_id"] == "b" and hits[0]["score"] == pytest.approx(1.0)
    assert hits[1]["score"] < 0.5


def test_store_metadata_filter():
    base = np.eye(3, DIM, dtype="float32")
    store = _store_with(base, ["a", "b", "c"], ["sop", "sop", "maintenance"])
    hits = store.search(base[0], k=3, where={"doc_type": "maintenance"})
    assert [h["chunk_id"] for h in hits] == ["c"]


def test_store_round_trip_persistence(tmp_path):
    rng = np.random.default_rng(5)
    vectors = rng.normal(size=(10, DIM)).astype("float32")
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    ids = [f"doc__c{i:04d}" for i in range(10)]
    store = _store_with(vectors, ids, ["sop"] * 10)
    path = tmp_path / "store.parquet"
    store.save(path)
    loaded = VectorStore.load(path)
    assert len(loaded) == 10 and loaded.embedder_name == "hashing_fallback"
    # Recall@1 == 1.0: each vector must retrieve itself first after reload.
    for i in range(10):
        assert loaded.search(vectors[i], k=1)[0]["chunk_id"] == ids[i]


def test_store_refuses_mismatched_embedder(tmp_path):
    store = _store_with(np.eye(2, DIM, dtype="float32"), ["a", "b"], ["sop", "sop"])
    store.require_embedder("hashing_fallback")       # ok
    with pytest.raises(ValueError):
        store.require_embedder("BAAI/bge-base-en-v1.5")


def test_store_rejects_duplicates_and_bad_shapes():
    store = VectorStore(dim=DIM, embedder_name="hashing_fallback")
    vec = np.eye(1, DIM, dtype="float32")
    meta = pd.DataFrame({"doc_type": ["sop"]})
    store.add(["a"], vec, meta)
    with pytest.raises(ValueError):
        store.add(["a"], vec, meta)                  # duplicate id
    with pytest.raises(ValueError):
        store.add(["b"], np.ones((1, DIM + 1), dtype="float32"), meta)


# ------------------------------------------------------------------ index build helpers
def _chunks() -> pd.DataFrame:
    return pd.DataFrame([{
        "doc_id": "doc_x", "chunk_id": "doc_x__c0007", "doc_type": "sop",
        "text": "Inspect the spindle bearing for wear before restart.",
        "topic_tags": json.dumps(["spindle", "tool_wear"]), "n_tokens": 30,
    }])


def test_citation_format():
    assert citation_for("doc_x__c0007", "sop") == "sop:doc_x§c0007"


def test_chunk_metadata_carries_citation_and_tags():
    meta = chunk_metadata(_chunks())
    assert meta.loc[0, "citation"] == "sop:doc_x§c0007"
    assert meta.loc[0, "topic_tags"] == "spindle,tool_wear"


def test_sop_chunk_contract_sample_validates():
    assert validate_contract_sample(_chunks(), "hashing_fallback", DIM, n=1) == 1
