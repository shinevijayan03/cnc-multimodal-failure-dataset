"""Deterministic id generation — the backbone of idempotency.

The same input always yields the same id, so ``exists_and_fresh`` can safely
skip already-built outputs and re-runs reproduce identical cross-modal links.
"""

from __future__ import annotations

import hashlib

_HASH_LEN = 12  # hex chars of the sha1 digest to keep ids short but collision-resistant


def stable_hash(*parts: str) -> str:
    """Short, stable hex digest of the given string parts.

    Parts are joined with a delimiter that cannot appear in a normal path so
    distinct tuples cannot collide by concatenation (e.g. ("a","bc") vs
    ("ab","c")).
    """
    joined = "\x1f".join(parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:_HASH_LEN]


def incident_id(source_dataset: str, run_id: str, t_event_s: float) -> str:
    """Stable id for an incident window.

    Rounded event time keeps the id stable across float-formatting noise while
    still distinguishing events that differ by >=1 ms.
    """
    t_key = format(round(float(t_event_s), 3), ".3f")
    return f"inc_{source_dataset}_{stable_hash(source_dataset, run_id, t_key)}"


def video_id(source: str, rel_path: str) -> str:
    """Stable id for a video clip, derived from its source label and path."""
    return f"vid_{stable_hash(source, rel_path)}"


def doc_id(rel_path: str) -> str:
    """Stable id for a text document, derived from its relative path."""
    return f"doc_{stable_hash(rel_path)}"


def chunk_id(doc: str, ordinal: int) -> str:
    """Stable id for the *ordinal*-th chunk of document *doc*."""
    return f"{doc}__c{ordinal:04d}"
