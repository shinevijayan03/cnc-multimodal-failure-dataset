from __future__ import annotations

import pytest
from pydantic import ValidationError

from contracts import ChainClaim, ExplanationOutput, SubCause
from src.eval.fixtures import corrupted_intervals_fixture, mixed_fixture, oracle_fixture
from src.eval.metrics import compute_metrics, interval_iou


def test_interval_iou_exact_and_disjoint():
    assert interval_iou((0.0, 10.0), (0.0, 10.0)) == 1.0
    assert interval_iou((0.0, 5.0), (10.0, 15.0)) == 0.0


def test_oracle_fixture_scores_as_faithful():
    fixture = oracle_fixture()
    metrics = compute_metrics(fixture.outputs, fixture.gold)
    assert metrics["schema_valid_rate"] == 1.0
    assert metrics["unsupported_claim_rate"] <= 0.05
    assert metrics["attr_precision"] >= 0.95
    assert metrics["attr_recall"] >= 0.95
    assert metrics["mean_iou_sensor"] >= 0.95
    assert metrics["iou_sensor"] >= 0.95
    assert metrics["f1"] >= 0.95
    assert metrics["auroc"] >= 0.95
    assert metrics["top1_subcause"] >= 0.95


def test_corrupted_intervals_lower_temporal_iou():
    fixture = corrupted_intervals_fixture()
    metrics = compute_metrics(fixture.outputs, fixture.gold)
    assert metrics["mean_iou_sensor"] < 0.2
    assert metrics["iou_sensor"] < 0.2
    assert metrics["wrong_time_claim_rate"] > 0.5


def test_metric_monotonicity_for_interval_corruption():
    ratios = [0.0, 0.5, 1.0]
    ious = [compute_metrics(mixed_fixture(ratio).outputs, mixed_fixture(ratio).gold)["mean_iou_sensor"]
            for ratio in ratios]
    assert ious == sorted(ious, reverse=True)


def test_reversed_chain_is_schema_invalid():
    with pytest.raises(ValidationError, match="chronologically ordered"):
        ExplanationOutput(
            incident_id="inc_bad",
            predicted_failure_label="abnormal_vibration",
            root_cause_ranked=[SubCause.TOOL_WEAR],
            chronological_evidence_chain=[
                ChainClaim(t_start=0.0, t_end=1.0, claim="later", evidence_ids=["a"]),
                ChainClaim(t_start=-5.0, t_end=-4.0, claim="earlier", evidence_ids=["b"]),
            ],
            sop_linkage=[],
            confidence=0.5,
            uncertainty="invalid fixture",
            corrective_action="none",
        )
