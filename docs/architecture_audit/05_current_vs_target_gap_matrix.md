# 05 — Current vs Target Gap Matrix

Legend — Gap: Implemented / Partially Implemented / Stub Only / Missing /
Unknown / Incorrectly Implemented / Needs Deep Build. Severity: Critical/High/
Medium/Low. Effort: Small/Medium/Large/Research-Prototype (R/P).

| # | Target Component | Expected Capability | Current Implementation | Evidence | Gap Type | Severity | Effort | Priority |
|---|---|---|---|---|---|---|---|---|
| 1 | Raw vibration ingestion | Load vibration_x/y/z time-series | `read_generic_csv`, `read_bosch_h5`, `Normalizer` → canonical ax/ay/az | `src/etl/sensor_etl.py:67-131`; dry-run OK | Implemented | — | — | — |
| 2 | Incident window selection | t=-12s..0s pre-alarm window | `EventDetector`+`WindowCarver` carve ±8s around detected event, incident-relative `t_rel_s` | `src/etl/sensor_etl.py:224-377`; `config windowing` | Partially Implemented (window convention differs; no alarm anchor) | Medium | Small | P2 |
| 3 | Timestamp normalization | Raw → incident-relative time across modalities | Sensor: yes (`t_rel_s`). Video/SOP: constructed alignment only | `sensor_etl.WindowCarver`; ledger `sync_provenance: constructed` | Partially Implemented | High | Medium | P8 |
| 4 | Patch creation | Window → patch tokens | None | no patching code anywhere | Missing | Critical | Medium | P3 |
| 5 | PatchTST/TimesNet/1D CNN encoder | Trainable vibration encoder → Hvib | None (`docs/_sdd/tasks.md` T-10/T-11 "Not started") | no `src/encoder/` | Missing / Needs Deep Build | Critical | Large | P4 |
| 6 | Degradation signature learning | Learn RMS rise, band increase, abnormal variance | Heuristic threshold features only; no learning | `sensor_etl.EvidenceSpanExtractor`; `features/vibration.py` | Missing (heuristic seed exists) | Critical | Large | P4 |
| 7 | Sensor summary generation | sensor_summary, anomaly_score, predicted_sensor_state, important_sensor_interval | Evidence spans exist; no summary text/anomaly score generator | `sensor_relevant_spans` in `incidents.parquet` | Partially Implemented | High | Medium | P3 |
| 8 | Video ingestion | Load machine video | ffmpeg probe/normalize to 720p/30fps mp4 | `src/etl/video_etl.py`; ffmpeg on PATH | Implemented | — | — | — |
| 9 | Video clip extraction | Clips around incident timeline | Whole short clips normalized; matching to incidents by label, not time | `video_etl`, `assemble.VideoMatcher` | Partially Implemented | High | Medium | P7 |
| 10 | QwenVL/LLaVA-NeXT-Video integration | Frozen VLM clip summarizer | None (T-12 "Not started") | no `src/vision/` | Missing / Needs Deep Build | Critical | Large + R/P | P7 |
| 11 | Video summary generation | wobble/oscillation/breakage summaries + confidence | `VideoClip.clip_summary` field exists, never populated | `contracts/core.py:72` | Stub Only (contract field) | High | Large | P7 |
| 12 | SOP/manual ingestion | Parse md/txt/docx/pdf | `DocReader` with page caps, type inference | `src/etl/text_etl.py:96-157`; dry-run OK | Implemented | — | — | — |
| 13 | Semantic chunking | Meaning-aware chunks | Token-target + heading-aware chunking; keyword topic tags (not embedding-semantic) | `text_etl.Chunker`, `TopicTagger` | Partially Implemented | Medium | Small | P5 |
| 14 | Embedding generation | Chunk embeddings (BGE declared) | Declared in contract only; no embedding code | `contracts/core.py::SOPChunk.embedding_model` | Missing | Critical | Medium | P5 |
| 15 | Vector DB | Persistent similarity search | None | no vector-store code/dep | Missing | Critical | Medium | P5 |
| 16 | Evidence graph | Nodes/edges across sensor/video/SOP/failure/mode | Alignment ledger (flat JSONL provenance) only; no graph store/queries | `docs/_data/alignment_ledger.jsonl`; T-13/T-15 not started | Missing (precursor exists) | Critical | Large | P6 |
| 17 | Retriever | Vector + graph + metadata retrieval | Keyword topic-map retrieval at dataset-build time only | `assemble.TextRetriever`; config `keyword_bm25` | Partially Implemented (build-time keyword only) | Critical | Large | P6 |
| 18 | Sensor+video query construction | Query built from sensor/clip summaries | None | — | Missing | High | Medium | P6 |
| 19 | Temporal grounding layer | Normalize + align + validate chronology | Contract `AlignedTuple` + per-modality spans; **no producer module** | `contracts/core.py:122-137` | Stub Only (schema without producer) | Critical | Large | P8 |
| 20 | Aligned evidence tuple creation | Emit aligned tuples per window | Same as #19 | same | Stub Only | Critical | Medium | P8 |
| 21 | Joint feature space | Project Hvib/Hvis/Htext | None | no `src/fusion/` | Missing | Critical | Large | P9 |
| 22 | Cross-modal fusion | Correlation/cross-attention | None | same | Missing / Needs Deep Build | Critical | Large + R/P | P9 |
| 23 | Cross-attention/correlation | Baseline correlation acceptable v1 | None | same | Missing | High | Medium | P9 |
| 24 | Evidence selection head | Rank/select top-K evidence | None (T-17/T-18 not started) | no `src/temporal/`, `src/fusion/` | Missing | Critical | Large | P10 |
| 25 | Decoder LLM prompt/template | Prompt assembly from evidence bundle | None (T-19/T-21 not started) | no `src/explain/` | Missing | Critical | Medium | P11 |
| 26 | Structured explanation generation | GBNF-constrained `ExplanationOutput` (I-9) | Output contract + validators exist; no generator | `contracts/explanation.py` | Stub Only (contract without generator) | Critical | Large + R/P | P11 |
| 27 | Evidence citation | Every claim ≥1 resolvable evidence_id (I-2) | Enforced in contract + scored in metrics; no producer | `ChainClaim.evidence_ids min_length=1`; `metrics.score_claims` | Partially Implemented (enforcement w/o generation) | High | — (rides on #26) | P11 |
| 28 | Chronology validation | Reject non-monotonic chains | `ExplanationOutput._monotone_chain` validator + `wrong_time_claim_rate` metric | `contracts/explanation.py:36-41`; `src/eval/metrics.py:171` | Implemented (at schema/metric level) | — | — | — |
| 29 | Evaluation metrics | F1/AUROC, top-K, IoU, recall@K, attribution, ECE | Implemented over **fixtures only**; AUROC & ECE are documented placeholders; dataset-quality eval separate & solid | `src/eval/metrics.py`; `src/evaluate.py`; runs PASS | Partially Implemented | High | Medium | P12 |
| 30 | Faithfulness audit | Automated audit incl. LLM judge | Rule-based sensor verifier real; LLM judge placeholder | `verify_sensor.py`, `verify_llm.py` | Partially Implemented | High | Large | P12 |
| 31 | Unsupported claim detection | Detect claims without support | `unsupported_claim_rate` + verifier; sensor-modality only has semantic check | `metrics.py:172,180` | Partially Implemented | Medium | Medium | P12 |
| 32 | Runtime app/demo | End-to-end explain demo | Dataset explorer only; no explanation flow | `streamlit_app.py`; smoke OK | Partially Implemented | High | Medium | P13 |
| 33 | API/UI interface | UI (and optional API) | Streamlit UI exists; no HTTP API | same | Partially Implemented | Low | Medium | P13 |
| 34 | Tests | Cover core modules | 107 tests across unit/integration/contracts/eval_meta/ui; 106 pass, 1 opt-in skip | `pytest -q` 2026-07-03 | Implemented (for existing scope) | — | — | ongoing |
| 35 | Documentation | Design + runbook docs | Extensive: README, docs/*, SDD, decision log | repo `docs/` | Implemented (for existing scope) | — | — | ongoing |

## Summary counts

- Implemented: 6 (raw sensor ingestion, video ingestion, SOP ingestion,
  chronology validation, tests, docs)
- Partially Implemented: 12
- Stub Only (contract/schema without producer): 4 (#11, #19, #20, #26)
- Missing / Needs Deep Build: 13
- Incorrectly Implemented: 0 found
- Unknown: 0 (all 35 components were resolvable from code + runtime)

**Headline finding:** the repository is a high-quality *data + evaluation
substrate* (Recipe A pipeline, contracts, metric harness, run-record
discipline) with **zero model-side components built** — everything from patch
creation (S1) through decoder generation (S8) is missing, and the eval harness
has never scored a real system output.
