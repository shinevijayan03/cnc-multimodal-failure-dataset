"""Multimodal fusion package (Build-A) — evidence selection + decoder context."""

from src.fusion.select import EvidenceBundle, EvidenceItem, select_evidence

__all__ = ["EvidenceBundle", "EvidenceItem", "select_evidence"]
