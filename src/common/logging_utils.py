"""Structured logging + a per-stage RunSummary.

Uses the standard library ``logging`` (the design permits stdlib in place of
loguru) with an optional JSON formatter so logs are machine-parseable when
``runtime.log_format: json``.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from typing import Any

_CONFIGURED = False


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Surface any structured extras attached via logger.info(..., extra={...}).
        for key, value in record.__dict__.items():
            if key in ("args", "msg", "levelname", "levelno", "name", "pathname",
                       "filename", "module", "exc_info", "exc_text", "stack_info",
                       "lineno", "funcName", "created", "msecs", "relativeCreated",
                       "thread", "threadName", "processName", "process", "taskName"):
                continue
            payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def get_logger(name: str = "recipe_a", level: str = "INFO", fmt: str = "json") -> logging.Logger:
    """Return the configured pipeline logger.

    Configures the root pipeline handler exactly once; repeated calls just hand
    back a child logger so every module logs through one consistent sink.
    """
    global _CONFIGURED
    root = logging.getLogger("recipe_a")
    if not _CONFIGURED:
        handler = logging.StreamHandler(sys.stderr)
        if fmt == "json":
            handler.setFormatter(_JsonFormatter())
        else:
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)-7s %(name)s | %(message)s",
                                  datefmt="%H:%M:%S")
            )
        root.handlers[:] = [handler]
        root.propagate = False
        _CONFIGURED = True
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    return root if name in ("recipe_a", "") else root.getChild(name)


@dataclass
class RunSummary:
    """Outcome counters for a single stage ``run()``.

    Stages return this instead of relying on log scraping, so integration tests
    can assert on counts directly.
    """

    stage: str
    discovered: int = 0           # raw units found (runs / files / clips)
    processed: int = 0            # units successfully processed
    written: int = 0              # output rows/files written (0 on dry-run)
    skipped: int = 0              # units skipped (disabled, unmappable, idempotent)
    errors: int = 0              # units that errored (caught & counted)
    dry_run: bool = False
    notes: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.errors == 0

    def bump(self, key: str, n: int = 1) -> None:
        setattr(self, key, getattr(self, key) + n)

    def note(self, key: str, value: Any) -> None:
        self.notes[key] = value

    def __str__(self) -> str:
        flag = " [DRY-RUN]" if self.dry_run else ""
        base = (f"[{self.stage}]{flag} discovered={self.discovered} "
                f"processed={self.processed} written={self.written} "
                f"skipped={self.skipped} errors={self.errors}")
        if self.notes:
            extras = " ".join(f"{k}={v}" for k, v in self.notes.items())
            base += f" | {extras}"
        return base
