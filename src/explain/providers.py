"""Decoder providers (Build-B).

`MockProvider` — deterministic template generator that assembles a
contract-valid explanation directly from the evidence bundle. It is the
always-available baseline and the CI test provider; its outputs are labeled
mode="mock" everywhere.

`LlamaCppProvider` — the real decoder per decision D2: a local GGUF
(Qwen2.5-7B-Instruct Q4_K_M) through llama.cpp with the I-9 GBNF grammar and
greedy decoding on the GPU (D11).
"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_GGUF = "models/gguf/Qwen2.5-7B-Instruct-Q4_K_M.gguf"

_SUBCAUSE_BY_FAMILY = {
    # deterministic failure_family -> ranked SubCause values (D6 taxonomy)
    "tool_wear": ["tool_wear_progression", "bearing_wear"],
    "chatter": ["mechanical_looseness", "imbalance"],
    "spindle_fault": ["bearing_wear", "imbalance"],
    "clamping_loss": ["mechanical_looseness", "misalignment"],
    "coolant_fault": ["bearing_wear", "tool_wear_progression"],
    "bearing_wear": ["bearing_wear", "imbalance"],
    "unknown": ["tool_wear_progression", "bearing_wear"],
}


class MockProvider:
    """Deterministic, schema-valid, evidence-grounded template decoder."""

    name = "mock_template_v1"
    mode = "mock"

    def generate(self, prompt: str, payload: dict) -> str:
        incident = payload["incident"]
        sensor = payload["sensor_items"]
        video = payload["video_items"]
        docs = payload["doc_items"]
        family = str(incident.get("failure_family", "unknown"))
        chain = []
        for item in sensor[:3]:
            chain.append({
                "t_start": item["t_start"], "t_end": item["t_end"],
                "claim": (f"Vibration anomaly score {item['score']:.3f} in "
                          f"{item['evidence_id']} ({item['alarm_state']})."),
                "evidence_ids": [item["evidence_id"]],
            })
        if video and sensor:
            top = sensor[0]
            chain.append({
                "t_start": max(top["t_start"], -60.0),
                "t_end": min(top["t_end"], 30.0),
                "claim": ("Video summary reports "
                          f"{video[0]['label'][:120]} (constructed sync)."),
                "evidence_ids": [video[0]["evidence_id"]],
            })
        if docs and sensor:
            top = sensor[0]
            chain.append({
                "t_start": max(top["t_start"], -60.0),
                "t_end": min(top["t_end"], 30.0),
                "claim": f"Documentation {docs[0]['label']} matches the symptom.",
                "evidence_ids": [docs[0]["evidence_id"]],
            })
        chain.sort(key=lambda c: c["t_start"])
        output = {
            "incident_id": str(incident.get("incident_id")),
            "predicted_failure_label": family,
            "root_cause_ranked": _SUBCAUSE_BY_FAMILY.get(
                family, _SUBCAUSE_BY_FAMILY["unknown"]),
            "chronological_evidence_chain": chain[:8],
            "sop_linkage": [d["label"] for d in docs[:3]],
            "confidence": round(min(0.9, max(0.1, (sensor[0]["score"]
                                                   if sensor else 0.1) + 0.3)), 2),
            "uncertainty": ("weak run-level labels; video sync constructed; "
                            "template decoder (mock)"),
            "corrective_action": (f"Follow {docs[0]['label']}" if docs
                                  else "Inspect spindle and tooling") +
            "; verify vibration trend after intervention.",
        }
        return json.dumps(output)


class LlamaCppProvider:
    """Local GGUF decoder with GBNF-constrained greedy decoding (I-9, D2)."""

    mode = "llm"

    def __init__(self, model_path: str = DEFAULT_GGUF, n_gpu_layers: int = -1,
                 n_ctx: int = 4096, max_tokens: int = 1200, seed: int = 20260702):
        from llama_cpp import Llama, LlamaGrammar

        from src.explain.grammar import explanation_grammar

        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(
                f"GGUF model not found: {path} — download per docs/runbook.md")
        self.name = path.stem
        self.max_tokens = max_tokens
        self._grammar = LlamaGrammar.from_string(explanation_grammar(),
                                                 verbose=False)
        self._llm = Llama(model_path=str(path), n_gpu_layers=n_gpu_layers,
                          n_ctx=n_ctx, seed=seed, verbose=False)

    def generate(self, prompt: str, payload: dict) -> str:
        result = self._llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,                    # greedy: deterministic (I-5)
            max_tokens=self.max_tokens,
            grammar=self._grammar,
        )
        return result["choices"][0]["message"]["content"]


def build_provider(kind: str, model_path: str = DEFAULT_GGUF,
                   n_gpu_layers: int = -1, max_tokens: int = 1200,
                   seed: int = 20260702):
    if kind == "mock":
        return MockProvider()
    if kind == "llama":
        return LlamaCppProvider(model_path=model_path, n_gpu_layers=n_gpu_layers,
                                max_tokens=max_tokens, seed=seed)
    raise ValueError(f"unknown decoder provider: {kind}")
