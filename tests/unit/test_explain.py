"""UT-EXP — Build-B decoder: grammar, providers, guardrails, prompt, UI."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from contracts import ExplanationOutput
from src.explain.generate import (
    apply_guardrails,
    build_prompt,
    generate_explanation,
    to_report,
)
from src.explain.grammar import GrammarError, explanation_grammar, json_schema_to_gbnf
from src.explain.providers import MockProvider, build_provider
from src.graph.evidence_graph import EvidenceGraph
from src.ui.workbench import incident_explanation


# ------------------------------------------------------------------ fixtures
def _graph() -> EvidenceGraph:
    g = EvidenceGraph()
    for node, kind in [("inc_a", "incident"), ("SW_inc_a_00", "window"),
                       ("SW_inc_a_01", "window"), ("doc_x__c0001", "chunk"),
                       ("vid.mp4", "video")]:
        g.add_node(node, kind)
    return g


def _incident() -> pd.Series:
    return pd.Series({"incident_id": "inc_a", "failure_family": "tool_wear",
                      "severity_label": "high", "regime_label": "unknown",
                      "video_file": "vid.mp4"})


def _bundle_rows() -> pd.DataFrame:
    return pd.DataFrame([
        {"incident_id": "inc_a", "modality": "sensor", "rank": 0,
         "evidence_id": "SW_inc_a_00", "score": 0.9, "confidence": 0.9,
         "label": "SW_inc_a_00 [-8.0s..+4.0s] event_in_window",
         "detail": "RMS 268.1, kurtosis 4.9"},
        {"incident_id": "inc_a", "modality": "sensor", "rank": 1,
         "evidence_id": "SW_inc_a_01", "score": 0.4, "confidence": 0.4,
         "label": "SW_inc_a_01 [-5.0s..+7.0s] event_in_window",
         "detail": "RMS 250.0"},
        {"incident_id": "inc_a", "modality": "video", "rank": 0,
         "evidence_id": "vid.mp4", "score": 0.95, "confidence": 0.95,
         "label": "VLM clip: chatter_marks", "detail": "Oscillatory motion."},
        {"incident_id": "inc_a", "modality": "document", "rank": 0,
         "evidence_id": "doc_x__c0001", "score": 0.76, "confidence": 0.66,
         "label": "sop:doc_x§c0001", "detail": "Inspect the spindle bearing."},
    ])


def _tuple_rows() -> pd.DataFrame:
    return pd.DataFrame([
        {"incident_id": "inc_a", "window_id": "SW_inc_a_00", "t_start": -8.0,
         "t_end": 4.0, "alarm_state": "event_in_window"},
        {"incident_id": "inc_a", "window_id": "SW_inc_a_01", "t_start": -5.0,
         "t_end": 7.0, "alarm_state": "event_in_window"},
    ])


def _valid_output(**overrides) -> ExplanationOutput:
    base = dict(
        incident_id="inc_a", predicted_failure_label="tool_wear",
        root_cause_ranked=["tool_wear_progression"],
        chronological_evidence_chain=[{
            "t_start": -8.0, "t_end": 4.0,
            "claim": "Vibration anomaly in SW_inc_a_00.",
            "evidence_ids": ["SW_inc_a_00"]}],
        sop_linkage=["sop:doc_x§c0001"], confidence=0.8,
        uncertainty="run-level labels", corrective_action="Inspect bearing.")
    base.update(overrides)
    return ExplanationOutput.model_validate(base)


# ------------------------------------------------------------------ grammar (I-9)
def test_explanation_grammar_compiles_from_contract_schema():
    gbnf = explanation_grammar()
    assert gbnf.startswith("root ::=")
    # Enum for SubCause must constrain to the D6 taxonomy.
    assert '"\\"tool_wear_progression\\""' in gbnf
    assert '"\\"bearing_wear\\""' in gbnf
    # Contract field names are baked into the grammar.
    for field in ("incident_id", "chronological_evidence_chain",
                  "corrective_action"):
        assert f'"\\"{field}\\""' in gbnf


def test_grammar_loads_in_llama_cpp():
    LlamaGrammar = pytest.importorskip("llama_cpp").LlamaGrammar
    grammar = LlamaGrammar.from_string(explanation_grammar(), verbose=False)
    assert grammar is not None


def test_grammar_compiler_rejects_unsupported_schema():
    with pytest.raises(GrammarError):
        json_schema_to_gbnf({"type": ["string", "number", "null"]})


# ------------------------------------------------------------------ mock provider
def test_mock_provider_emits_contract_valid_grounded_json():
    result = generate_explanation(_incident(), _bundle_rows(), _tuple_rows(),
                                  "CTX", _graph(), MockProvider())
    output = result["output"]
    assert output.incident_id == "inc_a"
    assert output.root_cause_ranked[0].value == "tool_wear_progression"
    ids = {e for c in output.chronological_evidence_chain for e in c.evidence_ids}
    assert ids == {"SW_inc_a_00", "SW_inc_a_01", "vid.mp4", "doc_x__c0001"}
    assert result["unsupported_claims"] == []
    assert result["mode"] == "mock"


def test_mock_provider_is_deterministic():
    a = generate_explanation(_incident(), _bundle_rows(), _tuple_rows(),
                             "CTX", _graph(), MockProvider())
    b = generate_explanation(_incident(), _bundle_rows(), _tuple_rows(),
                             "CTX", _graph(), MockProvider())
    assert a["output"] == b["output"] and a["report"] == b["report"]


def test_out_of_order_chain_is_repaired_deterministically():
    """7B sometimes emits grounded claims out of order; repair, don't reject."""
    class OutOfOrderProvider(MockProvider):
        def generate(self, prompt: str, payload: dict) -> str:
            data = json.loads(super().generate(prompt, payload))
            data["chronological_evidence_chain"].reverse()
            return json.dumps(data)

    result = generate_explanation(_incident(), _bundle_rows(), _tuple_rows(),
                                  "CTX", _graph(), OutOfOrderProvider())
    starts = [c.t_start for c in result["output"].chronological_evidence_chain]
    assert starts == sorted(starts)                      # contract satisfied
    assert result["chronology_repaired"] is True
    # An already-ordered chain is not flagged.
    clean = generate_explanation(_incident(), _bundle_rows(), _tuple_rows(),
                                 "CTX", _graph(), MockProvider())
    assert clean["chronology_repaired"] is False


def test_build_provider_rejects_unknown_and_missing_model(tmp_path):
    with pytest.raises(ValueError):
        build_provider("gpt4")
    with pytest.raises(FileNotFoundError):
        build_provider("llama", model_path=str(tmp_path / "missing.gguf"))


# ------------------------------------------------------------------ guardrails (I-2)
def test_guardrails_drop_unresolvable_claims():
    output = _valid_output(chronological_evidence_chain=[
        {"t_start": -8.0, "t_end": 4.0, "claim": "good claim",
         "evidence_ids": ["SW_inc_a_00"]},
        {"t_start": -5.0, "t_end": 7.0, "claim": "hallucinated evidence",
         "evidence_ids": ["SW_ghost_99"]},
    ])
    clean, unsupported = apply_guardrails(output, _graph(), [(-8.0, 4.0),
                                                             (-5.0, 7.0)])
    assert len(clean.chronological_evidence_chain) == 1
    assert "SW_ghost_99" in unsupported[0]


def test_guardrails_drop_alien_time_spans():
    output = _valid_output(chronological_evidence_chain=[
        {"t_start": -8.0, "t_end": 4.0, "claim": "in-window claim",
         "evidence_ids": ["SW_inc_a_00"]},
        {"t_start": 20.0, "t_end": 29.0, "claim": "claim outside all windows",
         "evidence_ids": ["SW_inc_a_00"]},
    ])
    clean, unsupported = apply_guardrails(output, _graph(), [(-8.0, 7.0)])
    assert len(clean.chronological_evidence_chain) == 1
    assert "overlaps no sensor sub-window" in unsupported[0]


def test_guardrails_refuse_fully_unsupported_output():
    output = _valid_output(chronological_evidence_chain=[
        {"t_start": -8.0, "t_end": 4.0, "claim": "only bad evidence",
         "evidence_ids": ["SW_ghost_99"]}])
    with pytest.raises(ValueError):
        apply_guardrails(output, _graph(), [(-8.0, 4.0)])


# ------------------------------------------------------------------ prompt + report
def test_prompt_contract_contains_schema_ids_and_rules():
    prompt = build_prompt("inc_a", "EVIDENCE BLOCK", ["SW_inc_a_00", "d1"])
    assert "incident_id to use: inc_a" in prompt
    assert '"SW_inc_a_00"' in prompt and "EVIDENCE BLOCK" in prompt
    assert "chronological_evidence_chain" in prompt      # schema embedded
    assert "constructed" in prompt                       # I-8 rule stated


def test_report_shape_matches_build_spec():
    result = generate_explanation(_incident(), _bundle_rows(), _tuple_rows(),
                                  "CTX", _graph(), MockProvider())
    report = result["report"]
    for key in ("failure_hypothesis", "chronology", "evidence", "sop_links",
                "corrective_actions", "confidence", "uncertainties",
                "unsupported_claims"):
        assert key in report
    assert set(report["evidence"]) == {"sensor", "video", "documents"}
    assert report["evidence"]["sensor"] == ["SW_inc_a_00", "SW_inc_a_01"]
    _ = to_report  # exported


# ------------------------------------------------------------------ UI helper
def test_incident_explanation_prefers_llm_over_mock():
    frame = pd.DataFrame([
        {"incident_id": "inc_a", "mode": "mock", "provider": "mock_template_v1",
         "valid": True, "report_json": json.dumps({"mode": "mock", "x": 1}),
         "latency_s": 0.0},
        {"incident_id": "inc_a", "mode": "llm", "provider": "qwen",
         "valid": True, "report_json": json.dumps({"mode": "llm", "x": 2}),
         "latency_s": 9.0},
    ])
    report = incident_explanation(frame, "inc_a")
    assert report["mode"] == "llm" and report["provider"] == "qwen"
    assert incident_explanation(frame, "inc_zz") is None
