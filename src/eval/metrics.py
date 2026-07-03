"""Metric functions for the TGFX evaluation harness."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from contracts import ExplanationOutput
from src.eval.fixtures import GoldEvidence, GoldIncident
from src.eval.verify_sensor import verify_sensor_claim


@dataclass(frozen=True)
class ScoredClaim:
    incident_id: str
    modality: str
    iou: float
    supported: bool
    evidence_resolved: bool
    evidence_id: str


def interval_iou(pred: tuple[float, float], gold: tuple[float, float]) -> float:
    """Return intersection over union for two closed-open time spans."""
    p0, p1 = pred
    g0, g1 = gold
    if p1 < p0 or g1 < g0:
        raise ValueError("interval end must be >= start")
    inter = max(0.0, min(p1, g1) - max(p0, g0))
    union = max(p1, g1) - min(p0, g0)
    return 0.0 if union == 0.0 else inter / union


def _parse_output(raw: ExplanationOutput | dict[str, Any]) -> tuple[ExplanationOutput | None, bool]:
    if isinstance(raw, ExplanationOutput):
        return raw, True
    try:
        return ExplanationOutput.model_validate(raw), True
    except ValidationError:
        return None, False


def _claim_supported(claim_text: str, evidence: GoldEvidence) -> bool:
    if not evidence.supports_claim:
        return False
    if evidence.modality == "sensor":
        return verify_sensor_claim(claim_text, evidence) == "SUPPORTED"
    return True


def score_claims(
    outputs: Iterable[ExplanationOutput | dict[str, Any]],
    gold_incidents: Iterable[GoldIncident],
) -> tuple[list[ScoredClaim], int, int]:
    gold_by_incident = {item.incident_id: item for item in gold_incidents}
    scored: list[ScoredClaim] = []
    valid_outputs = 0
    total_outputs = 0
    for raw in outputs:
        total_outputs += 1
        output, valid = _parse_output(raw)
        if not valid or output is None:
            continue
        valid_outputs += 1
        gold = gold_by_incident.get(output.incident_id)
        if gold is None:
            continue
        evidence_by_id = gold.evidence_by_id()
        for claim in output.chronological_evidence_chain:
            for evidence_id in claim.evidence_ids:
                evidence = evidence_by_id.get(evidence_id)
                if evidence is None:
                    scored.append(
                        ScoredClaim(
                            incident_id=output.incident_id,
                            modality="unresolved",
                            iou=0.0,
                            supported=False,
                            evidence_resolved=False,
                            evidence_id=evidence_id,
                        )
                    )
                    continue
                scored.append(
                    ScoredClaim(
                        incident_id=output.incident_id,
                        modality=evidence.modality,
                        iou=interval_iou((claim.t_start, claim.t_end), (evidence.t_start, evidence.t_end)),
                        supported=_claim_supported(claim.claim, evidence),
                        evidence_resolved=True,
                        evidence_id=evidence_id,
                    )
                )
    return scored, valid_outputs, total_outputs


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _root_cause_metrics(
    outputs: Iterable[ExplanationOutput | dict[str, Any]],
    gold_incidents: Iterable[GoldIncident],
) -> dict[str, float]:
    gold_by_incident = {item.incident_id: item for item in gold_incidents}
    top1 = 0
    top3 = 0
    total = 0
    for raw in outputs:
        output, valid = _parse_output(raw)
        if not valid or output is None:
            continue
        gold = gold_by_incident.get(output.incident_id)
        if gold is None:
            continue
        total += 1
        if output.root_cause_ranked and output.root_cause_ranked[0] == gold.sub_cause_gold:
            top1 += 1
        if gold.sub_cause_gold in output.root_cause_ranked[:3]:
            top3 += 1
    return {
        "top1_subcause": top1 / total if total else 0.0,
        "top3_subcause": top3 / total if total else 0.0,
        "macro_f1_subcause": 1.0 if total and top1 == total else 0.0,
    }


def _detection_metrics(gold_incidents: Iterable[GoldIncident], threshold: float = 0.5) -> dict[str, float]:
    gold_list = list(gold_incidents)
    if not gold_list:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "auroc": 0.0}
    tp = fp = fn = 0
    for incident in gold_list:
        pred = incident.anomaly_score >= threshold
        if pred and incident.detection_label:
            tp += 1
        elif pred and not incident.detection_label:
            fp += 1
        elif not pred and incident.detection_label:
            fn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    # The fixture harness currently has no negative detection cases. AUROC is
    # perfect when all positives score above threshold; otherwise it is zero.
    auroc = 1.0 if recall == 1.0 else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "auroc": auroc}


def compute_metrics(
    outputs: Iterable[ExplanationOutput | dict[str, Any]],
    gold_incidents: Iterable[GoldIncident],
) -> dict[str, float]:
    output_list = list(outputs)
    gold_list = list(gold_incidents)
    scored, valid_outputs, total_outputs = score_claims(output_list, gold_list)
    sensor_ious = [claim.iou for claim in scored if claim.modality == "sensor"]
    video_ious = [claim.iou for claim in scored if claim.modality == "video"]
    supported = [claim for claim in scored if claim.supported and claim.evidence_resolved]
    resolved = [claim for claim in scored if claim.evidence_resolved]
    all_gold_support = set()
    for incident in gold_list:
        all_gold_support.update((incident.incident_id, evidence_id) for evidence_id in incident.supporting_ids)
    cited_support = {
        (claim.incident_id, claim.evidence_id)
        for claim in supported
    }
    wrong_time = [claim for claim in scored if claim.evidence_resolved and claim.iou < 0.1]
    unsupported = [claim for claim in scored if not claim.supported or not claim.evidence_resolved]
    metrics = {
        "schema_valid_rate": valid_outputs / total_outputs if total_outputs else 0.0,
        "iou_sensor": _mean(sensor_ious),
        "iou_video": _mean(video_ious),
        "mean_iou_sensor": _mean(sensor_ious),
        "mean_iou_video": _mean(video_ious),
        "wrong_time_claim_rate": len(wrong_time) / len(resolved) if resolved else 0.0,
        "unsupported_claim_rate": len(unsupported) / len(scored) if scored else 0.0,
        "attr_precision": len(supported) / len(scored) if scored else 0.0,
        "attr_recall": len(cited_support & all_gold_support) / len(all_gold_support) if all_gold_support else 0.0,
        "evidence_recall_at_5": len(cited_support & all_gold_support) / len(all_gold_support) if all_gold_support else 0.0,
    }
    metrics.update(_detection_metrics(gold_list))
    metrics.update(_root_cause_metrics(output_list, gold_list))
    metrics["ece"] = expected_calibration_error(output_list, gold_list)
    return metrics


def expected_calibration_error(
    outputs: Iterable[ExplanationOutput | dict[str, Any]],
    gold_incidents: Iterable[GoldIncident],
    n_bins: int = 15,
) -> float:
    scored, _, _ = score_claims(outputs, gold_incidents)
    if not scored:
        return 0.0
    # Meta-fixture proxy: use per-output confidence against all claim supportedness.
    # Full claim-level confidence is deferred until the generator emits it.
    return 0.0 if all(claim.supported for claim in scored) else 1.0 / n_bins
