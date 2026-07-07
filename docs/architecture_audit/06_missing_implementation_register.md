# 06 — Missing Implementation Register

Components with **no runnable implementation** at commit `547f2c1`, grouped by
target subsystem. "Contract exists" means a pydantic schema is defined in
`contracts/` but nothing produces instances of it from real data.

## S1 Sensor pipeline

| ID | Missing capability | Contract exists? | Notes |
|---|---|---|---|
| M-01 | Patch creation (window → patch tokens) | No | Nothing in `src/features/` or `src/etl/` |
| M-02 | Trainable encoder (PatchTST/TimesNet/1D CNN) producing Hvib | No | No `src/encoder/`; no torch dependency in `pyproject.toml` |
| M-03 | Learned degradation signatures + anomaly_score | Partially (`SensorWindow` fields) | Only heuristic threshold spans exist |
| M-04 | Sensor summary text + predicted_sensor_state | `AlignedTuple.sensor_summary` field | No generator |
| M-05 | Spectral-band feature in the one feature path | `SensorWindow.spectral_energy` (4 bands) | `src/features/vibration.py` has rms/variance/kurtosis but **no spectral band function** |

## S2 Video pipeline

| ID | Missing capability | Contract exists? | Notes |
|---|---|---|---|
| M-06 | Incident-time clip extraction (vs label matching) | `VideoClip.t_start/t_end/frame_range` | Current matching is label-based, time alignment constructed |
| M-07 | Frozen VLM integration (Qwen2.5-VL primary; LLaVA-NeXT-Video comparison) | `VideoClip.clip_summary` | No `src/vision/`; no model deps |
| M-08 | Video summary + visual_labels + confidence + evidence IDs | `VideoClip.visual_labels` | Field never populated |

## S3 Text/RAG substrate

| ID | Missing capability | Contract exists? | Notes |
|---|---|---|---|
| M-09 | Embedding generation | `SOPChunk.embedding_model/dim` declared | No embedding code, no model dep |
| M-10 | Vector DB persistence + similarity search | No | No vector-store dependency at all |
| M-11 | Rich metadata tagging (equipment, subsystem, step number, alarm code, operating mode) | `SOPChunk.tags` dict | Current tags are topic keywords only (`TextChunkRow.topic_tags`) |

## S4 Retriever

| ID | Missing capability | Contract exists? | Notes |
|---|---|---|---|
| M-12 | Evidence graph (nodes/edges, traversal) | No | Only flat `alignment_ledger.jsonl` |
| M-13 | Runtime retriever (vector + graph + metadata filters) | No | `assemble.TextRetriever` is build-time keyword lookup only |
| M-14 | Sensor+video query construction | No | — |

## S5–S7 Grounding, fusion, selection

| ID | Missing capability | Contract exists? | Notes |
|---|---|---|---|
| M-15 | Temporal grounding producer (aligned tuples + chronology check over real data) | **Yes — `AlignedTuple`** | Schema validated by tests, zero producers |
| M-16 | Joint feature space / projection | No | — |
| M-17 | Cross-modal correlation / cross-attention | No | — |
| M-18 | Evidence selection head (top-K, confidence) | No | — |

## S8 Explanation generation

| ID | Missing capability | Contract exists? | Notes |
|---|---|---|---|
| M-19 | Decoder LLM interface (Gemma/Mistral/Qwen Instruct) | No | — |
| M-20 | Prompt template from evidence bundle | No | — |
| M-21 | GBNF grammar compiled from ExplanationOutput JSON Schema (I-9) | **Yes — `ExplanationOutput`** | No grammar compiler, no constrained decoding |
| M-22 | Baseline B1 (free-text) and other baselines | No | T-19/T-21 not started |

## S9 Evaluation

| ID | Missing capability | Contract exists? | Notes |
|---|---|---|---|
| M-23 | Eval over real system outputs (not fixtures) | Harness exists | `src/eval/run.py` only loads hand fixtures |
| M-24 | Real AUROC (needs negative cases) | Placeholder documented in `metrics.py:148-149` | — |
| M-25 | Real calibration/ECE | Proxy documented in `metrics.py:199-201` | — |
| M-26 | Generator-disjoint LLM judge | Placeholder `verify_llm.py` | Explicitly deferred in module docstring |
| M-27 | Temporal hallucination rate as defined for real outputs; human usefulness rubric ingestion | Partially (`wrong_time_claim_rate`) | — |
| M-28 | KPI gates G3, G7–G11 | `docs/_eval/gates.yaml` marks them fixture-only/deferred | — |

## S10 Demo

| ID | Missing capability | Contract exists? | Notes |
|---|---|---|---|
| M-29 | One-command end-to-end explain demo (sensor+video+SOP → explanation → audit) | No | Explorer UI shows dataset only |

## Also missing (cross-cutting)

- **Gold labels**: curated sub-cause ground truth. Current labels are weak
  deterministic scaffolding (`manifest.json label_status`); every learned
  component and metric above depends on at least a small curated gold set
  (the "golden mini-set" T-06 exists only as eval fixtures).
- **GPU/torch environment**: no ML runtime dependency is declared anywhere.
