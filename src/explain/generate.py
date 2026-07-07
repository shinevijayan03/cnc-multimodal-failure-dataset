"""Explanation generation + I-2 guardrails (Build-B).

Pipeline per incident: decoder context (Build-A) → prompt → provider (mock
template or GBNF-constrained local LLM) → JSON → `ExplanationOutput`
contract validation → guardrails:

  * every claim's evidence_ids must resolve in the evidence graph; claims
    with unresolvable ids are DROPPED and recorded in `unsupported_claims`
    (I-2: emitting them would be a schema violation);
  * claim spans must overlap the incident's real sub-window spans; claims
    with alien spans are dropped and recorded likewise.

Outputs both the constitution contract object and the report-shaped dict
(failure_hypothesis / chronology / evidence{sensor,video,documents} /
sop_links / corrective_actions / confidence / uncertainties /
unsupported_claims).

Usage:
    python -m src.explain.generate --config config/dataset.yaml --provider mock
    python -m src.explain.generate --provider llama --limit 20 --split val
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from pydantic import ValidationError

from contracts import ExplanationOutput
from src.common.config import PipelineConfig, load_config
from src.common.io_utils import read_parquet, write_parquet_atomic
from src.eval.run import _git_sha, _hash_payload, append_run_record
from src.explain.providers import build_provider
from src.graph.evidence_graph import EvidenceGraph, graph_path

EXPLANATIONS_FILENAME = "explanations.parquet"

_PROMPT_TEMPLATE = """You are a CNC failure analyst. Using ONLY the evidence \
below, produce the failure explanation as JSON matching the required schema. \
Rules: every claim must cite evidence ids exactly as given; time spans are \
incident-relative seconds inside [-60, 30] and must overlap the sensor \
sub-window spans; do not invent evidence; the video sync is constructed, so \
never attach a precise video timestamp; order claims chronologically.

Required JSON schema (produce exactly this shape):
{schema}

incident_id to use: {incident_id}
Allowed evidence ids: {allowed_ids}

EVIDENCE:
{context}

JSON:"""


def build_prompt(incident_id: str, context_text: str, allowed_ids: list[str]) -> str:
    schema = json.dumps(ExplanationOutput.model_json_schema(), sort_keys=True)
    return _PROMPT_TEMPLATE.format(schema=schema, incident_id=incident_id,
                                   allowed_ids=json.dumps(allowed_ids),
                                   context=context_text)


def _payload(incident: pd.Series, bundle_rows: pd.DataFrame,
             tuple_rows: pd.DataFrame) -> dict:
    span_by_window = ({str(r["window_id"]): (float(r["t_start"]), float(r["t_end"]))
                       for _, r in tuple_rows.iterrows()}
                      if not tuple_rows.empty else {})
    alarm_by_window = ({str(r["window_id"]): str(r["alarm_state"])
                        for _, r in tuple_rows.iterrows()}
                       if not tuple_rows.empty else {})
    sensor_items, video_items, doc_items = [], [], []
    for _, row in bundle_rows.iterrows():
        base = {"evidence_id": str(row["evidence_id"]),
                "score": float(row["score"]), "label": str(row["label"]),
                "detail": str(row["detail"])}
        if row["modality"] == "sensor":
            span = span_by_window.get(base["evidence_id"], (-12.0, 0.0))
            sensor_items.append({**base, "t_start": span[0], "t_end": span[1],
                                 "alarm_state": alarm_by_window.get(
                                     base["evidence_id"], "unknown")})
        elif row["modality"] == "video":
            video_items.append(base)
        else:
            doc_items.append(base)
    return {"incident": incident, "sensor_items": sensor_items,
            "video_items": video_items, "doc_items": doc_items,
            "window_spans": list(span_by_window.values())}


def apply_guardrails(output: ExplanationOutput, graph: EvidenceGraph,
                     window_spans: list[tuple[float, float]]
                     ) -> tuple[ExplanationOutput, list[str]]:
    """Drop I-2-violating claims; return (clean output, unsupported_claims)."""
    unsupported: list[str] = []
    kept = []
    for claim in output.chronological_evidence_chain:
        bad_ids = [e for e in claim.evidence_ids if not graph.resolves(e)]
        span_ok = (not window_spans) or any(
            claim.t_start <= hi and claim.t_end >= lo
            for lo, hi in window_spans)
        if bad_ids:
            unsupported.append(f"claim '{claim.claim[:80]}' cites unresolvable "
                               f"ids {bad_ids}")
        elif not span_ok:
            unsupported.append(f"claim '{claim.claim[:80]}' span "
                               f"[{claim.t_start},{claim.t_end}] overlaps no "
                               f"sensor sub-window")
        else:
            kept.append(claim)
    if not kept:
        raise ValueError("all claims failed guardrails — no grounded "
                         "explanation can be emitted (I-2)")
    clean = output.model_copy(update={"chronological_evidence_chain": kept})
    return clean, unsupported


def to_report(output: ExplanationOutput, payload: dict,
              unsupported: list[str], mode: str) -> dict:
    """The report shape required by the build spec (fable_prompt Phase 6)."""
    return {
        "failure_hypothesis": (f"{output.predicted_failure_label} — most likely "
                               f"{output.root_cause_ranked[0].value}"),
        "chronology": [
            {"t_start": c.t_start, "t_end": c.t_end, "claim": c.claim,
             "evidence_ids": list(c.evidence_ids)}
            for c in output.chronological_evidence_chain],
        "evidence": {
            "sensor": [i["evidence_id"] for i in payload["sensor_items"]],
            "video": [i["evidence_id"] for i in payload["video_items"]],
            "documents": [i["evidence_id"] for i in payload["doc_items"]],
        },
        "sop_links": list(output.sop_linkage),
        "corrective_actions": [output.corrective_action],
        "confidence": output.confidence,
        "uncertainties": [output.uncertainty],
        "unsupported_claims": unsupported,
        "mode": mode,
    }


def _canonicalize_chain(data: dict) -> tuple[dict, bool]:
    """Sort the claim chain by (t_start, t_end) — deterministic repair.

    The GBNF grammar guarantees shape, not claim ordering; the 7B model
    sometimes emits grounded claims out of chronological order, which the
    contract validator rejects wholesale. Sorting is a content-preserving
    canonicalization (claims and evidence ids untouched); whether it changed
    anything is reported as `chronology_repaired`.
    """
    chain = data.get("chronological_evidence_chain")
    if not isinstance(chain, list) or len(chain) < 2:
        return data, False
    ordered = sorted(chain, key=lambda c: (float(c.get("t_start", 0.0)),
                                           float(c.get("t_end", 0.0))))
    if ordered == chain:
        return data, False
    return {**data, "chronological_evidence_chain": ordered}, True


def generate_explanation(incident: pd.Series, bundle_rows: pd.DataFrame,
                         tuple_rows: pd.DataFrame, context_text: str,
                         graph: EvidenceGraph, provider) -> dict:
    payload = _payload(incident, bundle_rows, tuple_rows)
    allowed = [str(r["evidence_id"]) for _, r in bundle_rows.iterrows()]
    prompt = build_prompt(str(incident.get("incident_id")), context_text, allowed)
    started = time.perf_counter()
    raw = provider.generate(prompt, payload)
    latency = time.perf_counter() - started
    data, repaired = _canonicalize_chain(json.loads(raw))
    output = ExplanationOutput.model_validate(data)       # contract gate (G1)
    output, unsupported = apply_guardrails(output, graph,
                                           payload["window_spans"])
    return {"output": output,
            "report": to_report(output, payload, unsupported, provider.mode),
            "mode": provider.mode, "provider": provider.name,
            "unsupported_claims": unsupported,
            "chronology_repaired": repaired,
            "latency_s": round(latency, 2)}


# --------------------------------------------------------------------------- #
# Corpus driver
# --------------------------------------------------------------------------- #
def generate_corpus(cfg: PipelineConfig, provider_kind: str = "mock",
                    limit: int | None = None, split: str | None = None,
                    write: bool = True, model_path: str | None = None) -> dict:
    if split == "test":
        raise PermissionError("test split is quarantined (I-4)")
    processed = Path(cfg.paths.data_processed)
    incidents = read_parquet(cfg.paths.incidents_index)
    if split:
        incidents = incidents[incidents["split"] == split]
    bundles = read_parquet(processed / "evidence_bundles.parquet")
    contexts = read_parquet(processed / "decoder_contexts.parquet")
    tuples = read_parquet(processed / "aligned_tuples.parquet")
    graph = EvidenceGraph.load(graph_path(cfg))
    kwargs = {"model_path": model_path} if model_path else {}
    provider = build_provider(provider_kind, **kwargs)

    rows = []
    schema_failures = 0
    guardrail_drops = 0
    chronology_repairs = 0
    incident_frame = incidents.head(limit) if limit else incidents
    for _, incident in incident_frame.iterrows():
        inc_id = str(incident["incident_id"])
        bundle_rows = bundles[bundles["incident_id"] == inc_id]
        ctx = contexts[contexts["incident_id"] == inc_id]
        tuple_rows = tuples[tuples["incident_id"] == inc_id]
        if bundle_rows.empty or ctx.empty:
            continue
        try:
            result = generate_explanation(
                incident, bundle_rows, tuple_rows,
                str(ctx.iloc[0]["context_text"]), graph, provider)
        except (ValidationError, ValueError) as exc:
            schema_failures += 1
            rows.append({"incident_id": inc_id, "mode": provider.mode,
                         "provider": provider.name, "valid": False,
                         "error": str(exc)[:200], "report_json": "",
                         "n_claims": 0, "n_unsupported": 0,
                         "chronology_repaired": False, "latency_s": 0.0})
            continue
        guardrail_drops += len(result["unsupported_claims"])
        chronology_repairs += int(result["chronology_repaired"])
        rows.append({
            "incident_id": inc_id, "mode": result["mode"],
            "provider": result["provider"], "valid": True, "error": "",
            "report_json": json.dumps(result["report"]),
            "n_claims": len(result["output"].chronological_evidence_chain),
            "n_unsupported": len(result["unsupported_claims"]),
            "chronology_repaired": result["chronology_repaired"],
            "latency_s": result["latency_s"],
        })
    frame = pd.DataFrame(rows)
    out = processed / EXPLANATIONS_FILENAME
    if write and not frame.empty:
        if out.exists():
            # Merge: replace rows matching (incident_id, mode) of the new batch;
            # keep everything else (so mock and llm runs coexist per incident).
            old = read_parquet(out)
            replaced = (old["incident_id"].isin(frame["incident_id"])
                        & (old["mode"] == provider.mode))
            frame = pd.concat([old[~replaced], frame], ignore_index=True)
        write_parquet_atomic(frame, out)

    generated = frame[(frame["valid"]) & (frame["provider"] ==
                                          provider.name)] if len(frame) else frame
    metrics = {
        "incidents_attempted": int(len(incident_frame)),
        "explanations_valid": int(generated["incident_id"].nunique())
        if len(generated) else 0,
        "schema_valid_rate": round(1.0 - schema_failures /
                                   max(1, len(incident_frame)), 4),
        "claims_total": int(generated["n_claims"].sum()) if len(generated) else 0,
        "unsupported_claims_dropped": guardrail_drops,
        "chronology_repairs": chronology_repairs,
        "mean_latency_s": round(float(generated["latency_s"].mean()), 2)
        if len(generated) else 0.0,
    }
    if write and len(frame):
        ts = datetime.now(ZoneInfo("Asia/Calcutta")).isoformat(timespec="seconds")
        append_run_record({
            "run_id": f"decoder_{provider_kind}_{ts.replace(':', '').replace('-', '')}",
            "ts": ts, "git_sha": _git_sha(),
            "config_hash": _hash_payload({"provider": provider.name,
                                          "split": split or "all"}),
            "seed": 20260702, "split": split or "all_non_quarantined",
            "system": f"decoder_{provider_kind}",
            "dataset_manifest_hash": _hash_payload(
                {"attempted": metrics["incidents_attempted"]}),
            "metrics": {k: v for k, v in metrics.items()
                        if isinstance(v, (int, float))},
            "gates": {"G1": metrics["schema_valid_rate"] == 1.0,
                      "G2": True},          # unresolvable claims are dropped/raise
            "notes": (f"Build-B decoder ({provider.name}); guardrails drop "
                      f"I-2-violating claims into unsupported_claims"),
        })
    return {**metrics, "out": out.as_posix() if write else None}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate failure explanations.")
    parser.add_argument("--config", default="config/dataset.yaml")
    parser.add_argument("--provider", choices=["mock", "llama"], default="mock")
    parser.add_argument("--model-path", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--split", default=None, choices=[None, "train", "val"])
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    print(json.dumps(generate_corpus(cfg, provider_kind=args.provider,
                                     limit=args.limit, split=args.split,
                                     write=not args.no_write,
                                     model_path=args.model_path),
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
