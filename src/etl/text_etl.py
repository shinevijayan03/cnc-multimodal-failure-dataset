"""Stage 2 — Text ETL.

Reads SOP/maintenance manuals (md/txt/docx/pdf), splits them into heading-aware
~150-200 token chunks, tags each chunk by topic, and writes
``text_chunks.parquet``. Independent of the sensor stage. See
``docs/software_design.md`` §6.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

from ..common.config import ChunkingCfg, PipelineConfig, TextCfg
from ..common.ids import chunk_id, doc_id
from ..common.io_utils import rows_to_df, write_parquet_atomic
from ..common.logging_utils import RunSummary, get_logger
from ..common.schemas import DocType, TextChunkRow

_FALLBACK_WARNED = False

# Keyword signals for per-chunk doc_type classification (a single combined manual
# then yields both SOP and maintenance chunks).
_MAINT_KW = ("maintenance", "lubricat", "service", "inspect", "replace", "clean",
             "grease", "repair", "troubleshoot", "wear", "fault", "alarm")
_SOP_KW = ("operation", "operating", "procedure", "setup", "set-up", "install",
           "program", "workpiece", "fixture", "startup", "shutdown", "safety")


# --------------------------------------------------------------------------- #
# Tokenizer abstraction (extensibility hook #2)
# --------------------------------------------------------------------------- #
class Tokenizer(Protocol):
    name: str
    def encode(self, text: str) -> list[int]: ...
    def decode(self, ids: list[int]) -> str: ...
    def count(self, text: str) -> int: ...


class _WhitespaceTokenizer:
    """Fallback tokenizer: one token == one whitespace-delimited word."""

    name = "whitespace"

    def __init__(self) -> None:
        self._vocab: list[str] = []

    def encode(self, text: str) -> list[int]:
        words = text.split()
        start = len(self._vocab)
        self._vocab.extend(words)
        return list(range(start, start + len(words)))

    def decode(self, ids: list[int]) -> str:
        return " ".join(self._vocab[i] for i in ids)

    def count(self, text: str) -> int:
        return len(text.split())


class _TiktokenTokenizer:
    name = "tiktoken_cl100k"

    def __init__(self) -> None:
        import tiktoken  # noqa: PLC0415

        self._enc = tiktoken.get_encoding("cl100k_base")

    def encode(self, text: str) -> list[int]:
        return self._enc.encode(text)

    def decode(self, ids: list[int]) -> str:
        return self._enc.decode(ids)

    def count(self, text: str) -> int:
        return len(self._enc.encode(text))


def make_tokenizer(kind: str, logger=None) -> Tokenizer:
    """Build the configured tokenizer, falling back to whitespace (warn once)."""
    global _FALLBACK_WARNED
    if kind.startswith("tiktoken"):
        try:
            return _TiktokenTokenizer()
        except Exception:  # noqa: BLE001
            if logger and not _FALLBACK_WARNED:
                logger.warning("tiktoken unavailable; using whitespace token estimate")
                _FALLBACK_WARNED = True
    return _WhitespaceTokenizer()


# --------------------------------------------------------------------------- #
# DocReader
# --------------------------------------------------------------------------- #
class DocReader:
    """Read a document to plain text, keeping markdown headings as boundaries."""

    def read(self, path: Path, max_pages: int | None = None) -> tuple[str, DocType]:
        suffix = path.suffix.lower().lstrip(".")
        if suffix in ("md", "markdown", "txt"):
            text = path.read_text(encoding="utf-8", errors="replace")
        elif suffix == "docx":
            text = self._read_docx(path)
        elif suffix == "pdf":
            text = self._read_pdf(path, max_pages=max_pages)
        else:
            raise ValueError(f"unsupported document format: {path.suffix}")
        return text, self._infer_doc_type(path, text)

    @staticmethod
    def _read_docx(path: Path) -> str:
        try:
            import docx  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError("reading .docx requires python-docx") from exc
        document = docx.Document(str(path))
        lines: list[str] = []
        for para in document.paragraphs:
            style = (para.style.name or "").lower() if para.style else ""
            if style.startswith("heading") and para.text.strip():
                lines.append(f"# {para.text.strip()}")
            else:
                lines.append(para.text)
        return "\n".join(lines)

    @staticmethod
    def _read_pdf(path: Path, max_pages: int | None = None) -> str:
        try:
            from pypdf import PdfReader  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError("reading .pdf requires pypdf") from exc
        reader = PdfReader(str(path))
        pages = []
        n_pages = len(reader.pages) if max_pages is None else min(max_pages, len(reader.pages))
        for i in range(n_pages):
            page = reader.pages[i]
            pages.append(page.extract_text() or "")
        return "\n\n".join(pages)

    @staticmethod
    def _infer_doc_type(path: Path, text: str) -> DocType:
        # Front-matter override (markdown): `doc_type: maintenance`.
        m = re.search(r"^doc_type:\s*(sop|maintenance)\s*$", text[:500], re.IGNORECASE | re.MULTILINE)
        if m:
            return DocType(m.group(1).lower())
        name = path.name.lower()
        if any(k in name for k in ("mainten", "service", "repair", "_mm", "mm_")):
            return DocType.maintenance
        if any(k in name for k in ("sop", "operat", "procedure", "_om", "om_")):
            return DocType.sop
        # Ambiguous filename: fall back to content keyword balance.
        return _classify_doc_type(text, DocType.sop)


# --------------------------------------------------------------------------- #
# Chunker
# --------------------------------------------------------------------------- #
class Chunker:
    def __init__(self, cfg: ChunkingCfg, tokenizer: Tokenizer):
        self.cfg = cfg
        self.tok = tokenizer

    def count_tokens(self, s: str) -> int:
        return self.tok.count(s)

    def _sections(self, text: str) -> list[str]:
        """Split into heading-bounded sections (one section if not respecting headings)."""
        if not self.cfg.respect_headings:
            return [text]
        sections: list[str] = []
        current: list[str] = []
        for line in text.splitlines():
            if line.lstrip().startswith("#"):
                if current:
                    sections.append("\n".join(current))
                # Keep the heading text (without #) as the start of the new section.
                current = [line.lstrip("#").strip()]
            else:
                current.append(line)
        if current:
            sections.append("\n".join(current))
        return sections

    def chunk(self, text: str) -> list[str]:
        """Return chunks, each within [min,max] tokens (except a lone remainder),
        never crossing a heading, with ~overlap_tokens overlap; oversized
        paragraphs are hard-split because windowing is done in token space.
        """
        target = self.cfg.target_tokens
        cap = self.cfg.max_tokens
        win = min(target, cap)
        step = max(1, win - self.cfg.overlap_tokens)
        chunks: list[str] = []
        for section in self._sections(text):
            collapsed = re.sub(r"[ \t]+", " ", section).strip()
            if not collapsed:
                continue
            ids = self.tok.encode(collapsed)
            if not ids:
                continue
            i = 0
            while i < len(ids):
                piece = ids[i:i + win]
                chunks.append(self.tok.decode(piece).strip())
                if i + win >= len(ids):
                    break
                i += step
        return [c for c in chunks if c]


# --------------------------------------------------------------------------- #
# TopicTagger
# --------------------------------------------------------------------------- #
class TopicTagger:
    def __init__(self, topic_keywords: dict[str, list[str]]):
        self.topic_keywords = {t: [k.lower() for k in kws] for t, kws in topic_keywords.items()}

    def tag(self, text: str) -> list[str]:
        low = text.lower()
        return [topic for topic, kws in self.topic_keywords.items()
                if any(kw in low for kw in kws)]


def _classify_doc_type(text: str, default: DocType) -> DocType:
    low = text.lower()
    maint = sum(low.count(k) for k in _MAINT_KW)
    sop = sum(low.count(k) for k in _SOP_KW)
    if maint > sop:
        return DocType.maintenance
    if sop > maint:
        return DocType.sop
    return default


def _bounded_pages(max_pages: int | None, dry_run_max_pages: int | None, dry_run: bool) -> int | None:
    if not dry_run or dry_run_max_pages is None:
        return max_pages
    if max_pages is None:
        return dry_run_max_pages
    return min(max_pages, dry_run_max_pages)


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
class TextETL:
    def __init__(self, cfg: PipelineConfig, logger=None):
        self.cfg = cfg
        self.log = logger or get_logger("text", cfg.runtime.log_level, cfg.runtime.log_format)
        tcfg: TextCfg = cfg.text
        self.reader = DocReader()
        self.tokenizer = make_tokenizer(tcfg.chunking.tokenizer, self.log)
        self.chunker = Chunker(tcfg.chunking, self.tokenizer)
        self.tagger = TopicTagger(tcfg.topic_keywords)

    def _discover(self) -> list[Path]:
        root = Path(self.cfg.paths.raw_text_root)
        if not root.exists():
            return []
        exts = {f".{e.lower()}" for e in self.cfg.text.input_formats}
        return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in exts)

    def run(self, limit: int | None = None, dry_run: bool | None = None) -> RunSummary:
        dry_run = self.cfg.runtime.dry_run if dry_run is None else dry_run
        summ = RunSummary(stage="text", dry_run=dry_run)
        rows: list[TextChunkRow] = []
        files = self._discover()
        summ.discovered = len(files)
        max_pages = _bounded_pages(
            self.cfg.text.max_pages_per_doc,
            self.cfg.text.dry_run_max_pages_per_doc,
            dry_run,
        )
        for path in files:
            if limit is not None and summ.processed >= limit:
                break
            try:
                text, default_type = self.reader.read(path, max_pages)
            except Exception as exc:  # noqa: BLE001 - skip unreadable docs
                summ.bump("skipped")
                self.log.warning("could not read doc, skipped",
                                 extra={"doc": str(path), "error": str(exc)})
                if self.cfg.runtime.fail_fast:
                    raise
                continue
            d_id = doc_id(path.relative_to(Path(self.cfg.paths.raw_text_root)).as_posix())
            pieces = self.chunker.chunk(text)
            for ordinal, piece in enumerate(pieces):
                try:
                    row = TextChunkRow(
                        doc_id=d_id,
                        chunk_id=chunk_id(d_id, ordinal),
                        doc_type=_classify_doc_type(piece, default_type),
                        text=piece,
                        topic_tags=self.tagger.tag(piece),
                        n_tokens=self.chunker.count_tokens(piece),
                    )
                except Exception as exc:  # noqa: BLE001 - never write an invalid row
                    summ.bump("errors")
                    self.log.warning("invalid chunk skipped",
                                     extra={"doc": str(path), "ordinal": ordinal,
                                            "error": str(exc)})
                    continue
                rows.append(row)
                summ.bump("written")
            summ.bump("processed")
            self.log.info("doc chunked", extra={"doc": path.name, "chunks": len(pieces)})

        if not dry_run and rows:
            write_parquet_atomic(rows_to_df(rows), self.cfg.paths.text_chunks)
            self.log.info("text chunks written",
                          extra={"path": self.cfg.paths.text_chunks, "rows": len(rows)})
        summ.note("docs", summ.processed)
        return summ
