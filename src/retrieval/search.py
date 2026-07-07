"""Query the SOP vector index from the command line (Build Phase 5).

Usage:
    python -m src.retrieval.search --query "bearing vibration threshold" --k 5
    python -m src.retrieval.search --query "coolant flow" --doc-type maintenance
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.common.config import load_config
from src.retrieval.embeddings import build_embedder
from src.retrieval.store import VectorStore


def search(cfg, query: str, k: int = 5, doc_type: str | None = None,
           device: str | None = None) -> list[dict]:
    store = VectorStore.load(Path(cfg.paths.vector_store))
    kind = "hashing" if store.embedder_name == "hashing_fallback" else "bge"
    embedder = build_embedder(kind, model_name=cfg.retrieval.model_name,
                              device=device or cfg.retrieval.device,
                              batch_size=cfg.retrieval.batch_size)
    store.require_embedder(embedder.name)
    query_vec = embedder.embed([query], queries=True)[0]
    where = {"doc_type": doc_type} if doc_type else None
    return store.search(query_vec, k=k, where=where)


def _println(text: str) -> None:
    """Console-encoding-safe print (PDF chunks carry cp1252-hostile bullets)."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Search the SOP vector index.")
    parser.add_argument("--config", default="config/dataset.yaml")
    parser.add_argument("--query", required=True)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--doc-type", choices=["sop", "maintenance"], default=None)
    parser.add_argument("--device", default=None)
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    hits = search(cfg, args.query, k=args.k, doc_type=args.doc_type,
                  device=args.device)
    for rank, hit in enumerate(hits, start=1):
        preview = " ".join(str(hit["text"]).split())[:140]
        _println(f"{rank}. [{hit['score']:.4f}] {hit['citation']} "
                 f"(topics: {hit['topic_tags'] or '-'})")
        _println(f"   {preview}...")
    if not hits:
        print(json.dumps({"hits": 0}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
