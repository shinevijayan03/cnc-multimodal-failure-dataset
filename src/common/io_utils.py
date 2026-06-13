"""Shared IO helpers: atomic Parquet writes, JSON-list (de)serialization, and
idempotency checks.

The model<->DataFrame boundary lives here so every stage serializes rows the
same way: enums -> their string value, list fields -> JSON strings.
"""

from __future__ import annotations

import json
import os
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd
from pydantic import BaseModel

from .schemas import JSON_LIST_FIELDS


# --------------------------------------------------------------------------- #
# JSON-list columns
# --------------------------------------------------------------------------- #
def _jsonable(v: Any) -> Any:
    if isinstance(v, BaseModel):
        return v.model_dump()
    if isinstance(v, Enum):
        return v.value
    return v


def dump_json_col(values: Iterable[Any]) -> str:
    """Serialize a list field (``list[Span]`` or ``list[str]``) to a JSON string."""
    return json.dumps([_jsonable(v) for v in values], default=str)


def load_json_col(s: Any) -> list:
    """Inverse of :func:`dump_json_col`. Tolerates already-decoded lists and nulls."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return []
    if isinstance(s, list):
        return s
    return json.loads(s)


# --------------------------------------------------------------------------- #
# model <-> DataFrame
# --------------------------------------------------------------------------- #
def model_to_record(m: BaseModel) -> dict[str, Any]:
    """Flat dict ready for a DataFrame row: enums -> value, list fields -> JSON."""
    json_fields = JSON_LIST_FIELDS.get(type(m), ())
    record: dict[str, Any] = {}
    for name, value in m.__dict__.items():
        if name in json_fields:
            record[name] = dump_json_col(value or [])
        elif isinstance(value, Enum):
            record[name] = value.value
        else:
            record[name] = value
    return record


def rows_to_df(rows: Sequence[BaseModel]) -> pd.DataFrame:
    """Build a DataFrame from validated rows (empty frame if no rows)."""
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([model_to_record(r) for r in rows])


# --------------------------------------------------------------------------- #
# Parquet IO
# --------------------------------------------------------------------------- #
def write_parquet_atomic(df: pd.DataFrame, path: str | Path) -> None:
    """Write *df* to *path* atomically (temp file -> fsync -> os.replace).

    A crash mid-write leaves the original file (if any) untouched and no
    half-written file at the destination path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        df.to_parquet(tmp, index=False)
        # Best-effort durability before the atomic rename. fsync on a read-only
        # handle is rejected on Windows, so open read-write and tolerate failure;
        # the real atomicity guarantee is os.replace below.
        try:
            with open(tmp, "r+b") as fh:
                os.fsync(fh.fileno())
        except OSError:
            pass
        os.replace(tmp, path)  # atomic on POSIX and Windows for same-volume paths
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def read_parquet(path: str | Path) -> pd.DataFrame:
    return pd.read_parquet(Path(path))


# --------------------------------------------------------------------------- #
# Paths & idempotency
# --------------------------------------------------------------------------- #
def resolve_path(p: str | Path, root: str | Path) -> Path:
    """Resolve *p* to an absolute path, rooted at *root* when *p* is relative."""
    p = Path(p)
    return p if p.is_absolute() else (Path(root) / p)


def exists_and_fresh(out: str | Path, *inputs: str | Path) -> bool:
    """True iff *out* exists and is at least as new as every existing input.

    Used to skip rebuilding outputs whose inputs have not changed. If an input
    path does not exist it is ignored (treated as "no constraint").
    """
    out = Path(out)
    if not out.exists():
        return False
    out_mtime = out.stat().st_mtime
    for inp in inputs:
        inp = Path(inp)
        if inp.exists() and inp.stat().st_mtime > out_mtime:
            return False
    return True
