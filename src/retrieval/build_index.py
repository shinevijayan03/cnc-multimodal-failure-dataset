"""Build the SOP/maintenance vector index (Build Phase 5).

Reads text_chunks.parquet, validates a sample of rows against the `SOPChunk`
contract, embeds every chunk (BGE on the local GPU per D11, or the clearly
named hashing fallback), and persists the vector store with rich metadata
(doc_id, doc_type, topic tags, section/citation reference).

Usage:
    python -m src.retrieval.build_index --config config/dataset.yaml
    python -m src.retrieval.search --query "bearing vibration" --k 5
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd

from contracts import SOPChunk
from src.common.config import PipelineConfig, load_config
from src.common.io_utils import load_json_col, read_parquet
from src.retrieval.embeddings import build_embedder
from src.retrieval.store import VectorStore


def citation_for(chunk_id: str, doc_type: str) -> str:
    """Human-quotable citation: `sop:doc_9b792f…§c0021`."""
    doc, _, ordinal = chunk_id.rpartition("__")
    return f"{doc_type}:{doc}§{ordinal}"


def chunk_metadata(chunks: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "doc_id": chunks["doc_id"].astype(str),
        "doc_type": chunks["doc_type"].astype(str),
        "citation": [citation_for(str(c), str(t))
                     for c, t in zip(chunks["chunk_id"], chunks["doc_type"])],
        "topic_tags": [",".join(str(x) for x in load_json_col(v))
                       for v in chunks["topic_tags"]],
        "n_tokens": chunks["n_tokens"].astype(int),
        "text": chunks["text"].astype(str),
    })


def validate_contract_sample(chunks: pd.DataFrame, embedder_name: str,
                             dim: int, n: int = 5) -> int:
    validated = 0
    for _, row in chunks.head(n).iterrows():
        SOPChunk(
            chunk_id=str(row["chunk_id"]),
            doc_id=str(row["doc_id"]),
            section_ref=citation_for(str(row["chunk_id"]), str(row["doc_type"])),
            text=str(row["text"]),
            tags={"doc_type": str(row["doc_type"]),
                  "topics": ",".join(str(x) for x in load_json_col(row["topic_tags"]))},
            embedding_model=embedder_name,
            embedding_dim=dim,
        )
        validated += 1
    return validated


def build_index(cfg: PipelineConfig, kind: str | None = None,
                device: str | None = None, limit: int | None = None,
                write: bool = True) -> dict:
    rcfg = cfg.retrieval
    chunks = read_parquet(cfg.paths.text_chunks)
    if limit:
        chunks = chunks.head(limit)
    embedder = build_embedder(kind or rcfg.embedder, model_name=rcfg.model_name,
                              device=device or rcfg.device,
                              batch_size=rcfg.batch_size)
    validated = validate_contract_sample(chunks, embedder.name, embedder.dim)

    started = time.perf_counter()
    vectors = embedder.embed(chunks["text"].astype(str).tolist())
    elapsed = time.perf_counter() - started

    store = VectorStore(dim=embedder.dim, embedder_name=embedder.name)
    store.add(list(chunks["chunk_id"].astype(str)), vectors,
              chunk_metadata(chunks))
    out_path = Path(cfg.paths.vector_store)
    if write:
        store.save(out_path)
    return {
        "chunks": len(store),
        "dim": embedder.dim,
        "embedder": embedder.name,
        "contract_validated": validated,
        "embed_seconds": round(elapsed, 2),
        "out": out_path.as_posix() if write else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the SOP vector index.")
    parser.add_argument("--config", default="config/dataset.yaml")
    parser.add_argument("--kind", choices=["bge", "hashing"], default=None)
    parser.add_argument("--device", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    summary = build_index(cfg, kind=args.kind, device=args.device,
                          limit=args.limit, write=not args.no_write)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
