"""Placeholder LLM judge interface for TGFX evaluation.

The full generator-disjoint LLM judge is deferred. This module provides a stable
interface and deterministic fixture behavior so metric meta-tests can execute
without external credentials.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

JudgeVerdict = Literal["SUPPORTED", "PARTIAL", "UNSUPPORTED"]

PROMPT_VERSION = "tgfx_judge_v0_fixture_only"


@dataclass(frozen=True)
class JudgeResult:
    verdict: JudgeVerdict
    justification: str
    prompt_version: str = PROMPT_VERSION


def judge_claim_fixture_only(claim: str, evidence_text: str) -> JudgeResult:
    """Deterministic stand-in for fixture/meta-test use only."""
    low = claim.lower()
    evidence = evidence_text.lower()
    if "smoke" in low and "smoke" not in evidence:
        return JudgeResult(verdict="UNSUPPORTED", justification="smoke is absent from evidence")
    if any(token in evidence for token in low.split()[:3]):
        return JudgeResult(verdict="SUPPORTED", justification="fixture lexical support")
    return JudgeResult(verdict="PARTIAL", justification="fixture lexical overlap is weak")

