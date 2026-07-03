"""Rule-based verifier for TGFX sensor claims."""

from __future__ import annotations

from typing import Literal

from src.eval.fixtures import GoldEvidence
from src.features.vibration import rose

Verdict = Literal["SUPPORTED", "UNSUPPORTED", "UNVERIFIABLE"]


def verify_sensor_claim(claim: str, evidence: GoldEvidence) -> Verdict:
    """Verify simple sensor feature claims against fixture evidence.

    This starts the deterministic path required by the TGFX spec. It supports
    the meta-fixture grammar needed now: claims mentioning RMS/energy/kurtosis/
    variance and "rose/increased" must have current >= baseline + 20%.
    """
    if evidence.baseline_value is None or evidence.current_value is None:
        return "UNVERIFIABLE"
    text = claim.lower()
    feature_terms = ("rms", "energy", "kurtosis", "variance", "vibration")
    rise_terms = ("rose", "increased", "rise", "spiked")
    if any(term in text for term in feature_terms) and any(term in text for term in rise_terms):
        return "SUPPORTED" if rose(evidence.current_value, evidence.baseline_value) else "UNSUPPORTED"
    return "UNVERIFIABLE"

