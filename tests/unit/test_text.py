"""Text ETL tests — UT-TEXT-01..08, IT-TEXT-01."""

from __future__ import annotations

import pytest

from src.common.config import ChunkingCfg
from src.etl.text_etl import Chunker, DocReader, TopicTagger, _WhitespaceTokenizer, make_tokenizer

WS = _WhitespaceTokenizer
KW = {"vibration": ["vibration", "chatter"], "tool_wear": ["tool wear", "worn"]}


def _chunker(**over):
    base = dict(target_tokens=30, min_tokens=10, max_tokens=60, overlap_tokens=5,
                respect_headings=True, tokenizer="whitespace")
    base.update(over)
    return Chunker(ChunkingCfg(**base), _WhitespaceTokenizer())


def test_chunk_token_bounds():  # UT-TEXT-01
    text = "# Section\n" + " ".join(f"w{i}" for i in range(100))
    chunks = _chunker().chunk(text)
    counts = [len(c.split()) for c in chunks]
    assert all(c <= 60 for c in counts)
    assert all(c >= 10 for c in counts[:-1])               # lone remainder may be short


def test_no_cross_heading_chunk():  # UT-TEXT-02
    text = ("# Alpha\n" + " ".join(["alphaword"] * 40) +
            "\n# Beta\n" + " ".join(["betaword"] * 40))
    chunks = _chunker().chunk(text)
    assert all(not ("alphaword" in c and "betaword" in c) for c in chunks)


def test_overlap_honored():  # UT-TEXT-03
    text = " ".join(f"w{i}" for i in range(100))           # one heading-less section
    chunks = _chunker(overlap_tokens=5).chunk(text)
    assert len(chunks) >= 2
    prev_tail = chunks[0].split()[-5:]
    next_head = chunks[1].split()[:5]
    assert prev_tail == next_head


def test_giant_paragraph_hard_split():  # UT-TEXT-04
    text = " ".join(["x"] * 200)                            # no headings, > max
    chunks = _chunker(max_tokens=60, target_tokens=50).chunk(text)
    assert len(chunks) >= 4
    assert all(len(c.split()) <= 60 for c in chunks)


def test_token_count_fallback():  # UT-TEXT-05
    # whitespace tokenizer is the fallback used when tiktoken is unavailable.
    tok = make_tokenizer("whitespace")
    assert isinstance(tok, _WhitespaceTokenizer)
    assert tok.count("one two three") == 3
    # encode/decode round-trips through the whitespace vocab.
    assert tok.decode(tok.encode("alpha beta")) == "alpha beta"


def test_topic_tagging_hit():  # UT-TEXT-06
    tags = TopicTagger(KW).tag("we observed chatter and tool wear on the part")
    assert "vibration" in tags and "tool_wear" in tags


def test_no_spurious_tags():  # UT-TEXT-07
    assert TopicTagger(KW).tag("the weather is pleasant today") == []


def test_docx_read_or_skip(tmp_path):  # UT-TEXT-08
    docx = pytest.importorskip("docx")
    path = tmp_path / "tiny.docx"
    doc = docx.Document()
    doc.add_heading("Maintenance", level=1)
    doc.add_paragraph("Inspect the spindle bearing for wear.")
    doc.save(str(path))
    text, doc_type = DocReader().read(path)
    assert "spindle bearing" in text
    assert doc_type.value == "maintenance"
