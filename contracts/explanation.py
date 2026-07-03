"""TGFX explanation output contract.

Source: C:/Users/Admin/Downloads/master_prompt.md, section 3.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from .core import SubCause


class ChainClaim(BaseModel):
    t_start: float
    t_end: float
    claim: str = Field(max_length=300)
    evidence_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_span(self) -> "ChainClaim":
        if not (-60.0 <= self.t_start <= self.t_end <= 30.0):
            raise ValueError("claim span must be ordered inside [-60.0, +30.0]")
        return self


class ExplanationOutput(BaseModel):
    incident_id: str
    predicted_failure_label: str
    root_cause_ranked: list[SubCause] = Field(min_length=1, max_length=5)
    chronological_evidence_chain: list[ChainClaim] = Field(min_length=1, max_length=8)
    sop_linkage: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    uncertainty: str
    corrective_action: str

    @model_validator(mode="after")
    def _monotone_chain(self) -> "ExplanationOutput":
        starts = [claim.t_start for claim in self.chronological_evidence_chain]
        if starts != sorted(starts):
            raise ValueError("chain must be chronologically ordered")
        return self
