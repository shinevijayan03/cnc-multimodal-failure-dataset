from __future__ import annotations

import pytest
from pydantic import ValidationError

from contracts import ChainClaim, ExplanationOutput, SubCause


def _output(**overrides):
    data = {
        "incident_id": "inc_001",
        "predicted_failure_label": "abnormal_vibration",
        "root_cause_ranked": [SubCause.TOOL_WEAR],
        "chronological_evidence_chain": [
            ChainClaim(
                t_start=-20.0,
                t_end=-10.0,
                claim="RMS increased before the alarm.",
                evidence_ids=["SW_inc_001_03"],
            ),
            ChainClaim(
                t_start=-5.0,
                t_end=0.0,
                claim="The linked SOP recommends stopping the machine.",
                evidence_ids=["SOP_4_2"],
            ),
        ],
        "sop_linkage": ["SOP_4_2"],
        "confidence": 0.8,
        "uncertainty": "constructed video sync",
        "corrective_action": "Inspect tool wear and confirm vibration source.",
    }
    data.update(overrides)
    return ExplanationOutput(**data)


def test_explanation_output_accepts_grounded_ordered_chain():
    out = _output()
    assert out.chronological_evidence_chain[0].evidence_ids == ["SW_inc_001_03"]


def test_chain_claim_requires_evidence_id():
    with pytest.raises(ValidationError):
        ChainClaim(t_start=-1.0, t_end=0.0, claim="unsupported", evidence_ids=[])


def test_explanation_rejects_non_monotone_chain():
    with pytest.raises(ValidationError, match="chronologically ordered"):
        _output(
            chronological_evidence_chain=[
                ChainClaim(t_start=0.0, t_end=1.0, claim="later", evidence_ids=["a"]),
                ChainClaim(t_start=-5.0, t_end=-4.0, claim="earlier", evidence_ids=["b"]),
            ]
        )


def test_chain_claim_rejects_out_of_incident_span():
    with pytest.raises(ValidationError, match=r"\[-60.0, \+30.0\]"):
        ChainClaim(t_start=-61.0, t_end=-60.0, claim="outside", evidence_ids=["a"])
