"""Hand-authored TGFX eval meta-fixtures.

The fixtures are intentionally tiny and deterministic. They exercise the metric
harness before model code exists.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal

from contracts import ChainClaim, ExplanationOutput, SubCause

Modality = Literal["sensor", "video", "sop"]


@dataclass(frozen=True)
class GoldEvidence:
    evidence_id: str
    modality: Modality
    t_start: float
    t_end: float
    supports_claim: bool = True
    baseline_value: float | None = None
    current_value: float | None = None


@dataclass(frozen=True)
class GoldIncident:
    incident_id: str
    sub_cause_gold: SubCause
    evidence: tuple[GoldEvidence, ...]
    detection_label: bool = True
    anomaly_score: float = 0.95

    @property
    def supporting_ids(self) -> set[str]:
        return {item.evidence_id for item in self.evidence if item.supports_claim}

    def evidence_by_id(self) -> dict[str, GoldEvidence]:
        return {item.evidence_id: item for item in self.evidence}


@dataclass(frozen=True)
class EvalFixture:
    name: str
    gold: tuple[GoldIncident, ...]
    outputs: tuple[ExplanationOutput | dict[str, Any], ...]


def oracle_fixture() -> EvalFixture:
    gold = (
        GoldIncident(
            incident_id="inc_oracle_001",
            sub_cause_gold=SubCause.TOOL_WEAR,
            evidence=(
                GoldEvidence(
                    evidence_id="SW_inc_oracle_001_00",
                    modality="sensor",
                    t_start=-20.0,
                    t_end=-10.0,
                    baseline_value=1.0,
                    current_value=1.35,
                ),
                GoldEvidence(
                    evidence_id="SOP_4_2",
                    modality="sop",
                    t_start=-20.0,
                    t_end=-10.0,
                ),
            ),
        ),
        GoldIncident(
            incident_id="inc_oracle_002",
            sub_cause_gold=SubCause.IMBALANCE,
            evidence=(
                GoldEvidence(
                    evidence_id="SW_inc_oracle_002_00",
                    modality="sensor",
                    t_start=-12.0,
                    t_end=0.0,
                    baseline_value=0.8,
                    current_value=1.1,
                ),
                GoldEvidence(
                    evidence_id="VC_inc_oracle_002_00",
                    modality="video",
                    t_start=-8.0,
                    t_end=0.0,
                ),
            ),
        ),
    )
    outputs = (
        ExplanationOutput(
            incident_id="inc_oracle_001",
            predicted_failure_label="abnormal_vibration",
            root_cause_ranked=[SubCause.TOOL_WEAR, SubCause.BEARING_WEAR],
            chronological_evidence_chain=[
                ChainClaim(
                    t_start=-20.0,
                    t_end=-10.0,
                    claim="Vibration RMS rose before the alarm.",
                    evidence_ids=["SW_inc_oracle_001_00"],
                ),
                ChainClaim(
                    t_start=-19.0,
                    t_end=-11.0,
                    claim="The SOP links this symptom to tool inspection.",
                    evidence_ids=["SOP_4_2"],
                ),
            ],
            sop_linkage=["SOP_4_2"],
            confidence=0.95,
            uncertainty="low",
            corrective_action="Inspect tool wear and validate spindle conditions.",
        ),
        ExplanationOutput(
            incident_id="inc_oracle_002",
            predicted_failure_label="abnormal_vibration",
            root_cause_ranked=[SubCause.IMBALANCE, SubCause.MISALIGNMENT],
            chronological_evidence_chain=[
                ChainClaim(
                    t_start=-12.0,
                    t_end=0.0,
                    claim="Vibration RMS rose in the final pre-alarm window.",
                    evidence_ids=["SW_inc_oracle_002_00"],
                ),
                ChainClaim(
                    t_start=-8.0,
                    t_end=0.0,
                    claim="The video shows visible oscillation near the event.",
                    evidence_ids=["VC_inc_oracle_002_00"],
                ),
            ],
            sop_linkage=[],
            confidence=0.9,
            uncertainty="constructed video sync",
            corrective_action="Check imbalance signatures and inspect rotating components.",
        ),
    )
    return EvalFixture(name="oracle", gold=gold, outputs=outputs)


def corrupted_intervals_fixture(shift_s: float = 25.0) -> EvalFixture:
    base = oracle_fixture()
    outputs: list[ExplanationOutput] = []
    for output in base.outputs:
        assert isinstance(output, ExplanationOutput)
        claims = []
        for claim in output.chronological_evidence_chain:
            claims.append(
                ChainClaim(
                    t_start=min(claim.t_start + shift_s, 29.0),
                    t_end=min(claim.t_end + shift_s, 30.0),
                    claim=claim.claim,
                    evidence_ids=list(claim.evidence_ids),
                )
            )
        outputs.append(output.model_copy(update={"chronological_evidence_chain": claims}))
    return EvalFixture(name="corrupted_intervals", gold=base.gold, outputs=tuple(outputs))


def mixed_fixture(corruption_ratio: float) -> EvalFixture:
    if not 0.0 <= corruption_ratio <= 1.0:
        raise ValueError("corruption_ratio must be within [0, 1]")
    oracle = oracle_fixture()
    corrupted = corrupted_intervals_fixture()
    n_corrupt = round(len(oracle.outputs) * corruption_ratio)
    outputs = list(deepcopy(oracle.outputs))
    for idx in range(n_corrupt):
        outputs[idx] = corrupted.outputs[idx]
    return EvalFixture(name=f"mixed_{corruption_ratio:.2f}", gold=oracle.gold, outputs=tuple(outputs))


def load_fixture(name: str) -> EvalFixture:
    if name == "oracle":
        return oracle_fixture()
    if name == "corrupted_intervals":
        return corrupted_intervals_fixture()
    if name.startswith("mixed_"):
        return mixed_fixture(float(name.split("_", 1)[1]))
    raise ValueError(f"unknown fixture: {name}")
