"""Incident-assembly unit tests — UT-ASM-01..12."""

from __future__ import annotations

import numpy as np

from src.common.config import SplitCfg, TextRetrievalCfg, VideoMatchCfg
from src.common.schemas import (
    AlignmentMethod,
    Condition,
    DocType,
    FailureFamily,
    IncidentRow,
    Regime,
    Severity,
)
from src.etl.assemble_incidents import LabelDeriver, SplitAssigner, TextRetriever, VideoMatcher
from tests.conftest import make_chunks, make_video_index


# --------------------------------------------------------------------------- LabelDeriver
def test_severity_buckets():  # UT-ASM-01
    d = LabelDeriver(amp_lo=10.0, amp_hi=20.0)
    assert d.severity(5.0) is Severity.low
    assert d.derive(amplitude=5.0)["severity_label"].value == "low"
    assert d.derive(amplitude=15.0)["severity_label"].value == "med"
    assert d.derive(amplitude=25.0)["severity_label"].value == "high"


def test_label_defaults():  # UT-ASM-02
    labels = LabelDeriver(None, None).derive(meta=None, amplitude=None)
    assert labels["regime_label"] is Regime.unknown
    assert labels["severity_label"].value == "unknown"
    assert labels["root_cause_label"] == "unknown"


def test_weak_failure_labels_from_amplitude_quantiles():
    d = LabelDeriver(amp_lo=10.0, amp_hi=20.0)
    assert d.failure_family(5.0) is FailureFamily.tool_wear
    assert d.failure_family(15.0) is FailureFamily.spindle_fault
    assert d.failure_family(25.0) is FailureFamily.chatter
    assert d.derive(amplitude=25.0)["root_cause_label"] == "weak_signal_chatter"


def test_weak_id_bucket_labels_are_deterministic():
    d = LabelDeriver()
    assert d.weak_failure_family("inc_123") is d.weak_failure_family("inc_123")
    assert d.weak_severity("inc_123") is d.weak_severity("inc_123")


# --------------------------------------------------------------------------- VideoMatcher
def _matcher(**over):
    base = dict(strategy="label_match", require_regime_match=True,
                require_condition_match=False, allow_reuse=True, fallback_to_idle=True)
    base.update(over)
    return VideoMatcher(make_video_index(), VideoMatchCfg(**base), np.random.default_rng(0))


def test_video_regime_match():  # UT-ASM-03
    clip, method = _matcher().match(Regime.roughing, Condition.unknown)
    assert clip is not None
    assert clip["regime_label"] == "roughing"
    assert method is AlignmentMethod.label_match


def test_idle_fallback():  # UT-ASM-04
    clip, method = _matcher().match(Regime.plunge, Condition.unknown)  # no plunge clip
    assert clip is not None and clip["regime_label"] == "idle"
    assert method is AlignmentMethod.idle_fallback


def test_no_match_no_fallback():  # UT-ASM-05
    clip, method = _matcher(fallback_to_idle=False).match(Regime.plunge, Condition.unknown)
    assert clip is None and method is AlignmentMethod.none


def test_seeded_pick_reproducible():  # UT-ASM-06
    idx = make_video_index(("roughing", "roughing", "roughing", "idle"))
    cfg = VideoMatchCfg()
    a = VideoMatcher(idx, cfg, np.random.default_rng(42)).match(Regime.roughing, Condition.unknown)
    b = VideoMatcher(idx, cfg, np.random.default_rng(42)).match(Regime.roughing, Condition.unknown)
    assert a[0]["video_id"] == b[0]["video_id"]


# --------------------------------------------------------------------------- TextRetriever
def _retr(failure_map):
    return TextRetriever(make_chunks(), TextRetrievalCfg(), failure_map)


def test_text_retrieve_count():  # UT-ASM-07
    ids = _retr({"unknown": ["vibration", "tool_wear"]}).retrieve(
        FailureFamily.unknown, DocType.sop, 1, 3)
    assert 1 <= len(ids) <= 3
    assert all(c.startswith("doc_a") for c in ids)          # all SOP chunks


def test_failure_to_topics_mapping():  # UT-ASM-08
    retr = TextRetriever(make_chunks(), TextRetrievalCfg(),
                         {"chatter": ["vibration", "spindle"]})
    ids = retr.retrieve(FailureFamily.chatter, DocType.maintenance, 1, 2)
    # maintenance chunks tagged 'spindle' should be preferred/returned
    assert all(c.startswith("doc_b") for c in ids) and len(ids) >= 1


def test_topic_relax_on_miss():  # UT-ASM-09
    ids = _retr({"unknown": ["nonexistent_topic"]}).retrieve(
        FailureFamily.unknown, DocType.sop, 1, 2)
    assert len(ids) >= 1                                     # relaxed, still returns chunks


# --------------------------------------------------------------------------- SplitAssigner
def _incident(i: int, source: str) -> IncidentRow:
    return IncidentRow(
        incident_id=f"inc_{i}", source_dataset=source, machine_family="cnc_mill",
        failure_family="unknown", window_start_s=0.0, window_end_s=90.0, fs_hz=2000.0,
        sensor_file="f.parquet", sensor_channels=["az"], sensor_relevant_spans=[],
        split="train")


def test_split_fractions():  # UT-ASM-10
    rows = [_incident(i, f"src_{i}") for i in range(100)]     # 100 singleton groups
    SplitAssigner(SplitCfg(), np.random.default_rng(1)).assign(rows)
    counts = {s: sum(1 for r in rows if r.split.value == s) for s in
              ("train", "val", "test", "human_eval")}
    assert abs(counts["train"] - 70) <= 2
    assert abs(counts["val"] - 15) <= 2
    assert abs(counts["test"] - 10) <= 2


def test_no_group_leakage():  # UT-ASM-11
    rows = [_incident(i, "same_source") for i in range(20)]  # one group
    SplitAssigner(SplitCfg(), np.random.default_rng(1)).assign(rows)
    assert len({r.split for r in rows}) == 1                 # all in one split


def test_split_reproducible():  # UT-ASM-12
    rows1 = [_incident(i, f"src_{i % 7}") for i in range(50)]
    rows2 = [_incident(i, f"src_{i % 7}") for i in range(50)]
    SplitAssigner(SplitCfg(), np.random.default_rng(5)).assign(rows1)
    SplitAssigner(SplitCfg(), np.random.default_rng(5)).assign(rows2)
    assert [r.split for r in rows1] == [r.split for r in rows2]
