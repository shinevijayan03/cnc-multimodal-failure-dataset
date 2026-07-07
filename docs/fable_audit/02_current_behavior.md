# 02 — Current Behavior

**User problem solved today:** given a CNC incident, an engineer opens one
workbench and sees synchronized evidence — the vibration signal with real
anomaly spans, the linked clip with a real frozen-VLM description, retrieved
SOP passages with real similarity scores, per-window learned anomaly scores,
and a contract-valid aligned-tuple chronology — all on one incident-relative
time axis, exportable as a JSON evidence report. The *generated narrative
explanation* (decoder LLM) does not exist yet (Phase 11).

| Workflow | Input | Processing Path | Output | Files Involved | Evidence | Status |
|---|---|---|---|---|---|---|
| Dataset build | raw CSVs/PDFs/MP4s | 4-stage ETL → join → split | `incidents.parquet` (1702) + indices | `src/etl/*`, `src/cli.py` | `evaluate --tier mvp` → GRADE: PASS this session | ✅ complete |
| Dataset quality gate | indices | tiered metrics + hard gates | eval_report.{json,md}, exit code | `src/evaluate.py` | same | ✅ complete |
| Sub-windowing (D10) | waveforms | 12 s/stride-3 carve + query window | `subwindows.parquet` (3399) | `src/tgfx/windows.py` | build run + 11 unit tests | ✅ complete |
| Sensor features | sub-windows | one-path RMS/4-band/kurtosis/variance + heuristic anomaly + important interval + sha256 | `sensor_features.parquet` | `src/tgfx/sensor_features.py`, `src/features/*` | build run + 20 tests + contract sample | ✅ complete |
| Encoder training | patch tokens | seeded GPU autoencoder → Hvib + anomaly | `hvib.parquet`, checkpoint, run record | `src/encoder/*` | run record `encoder_autoencoder_20260702_…`; val AUROC 0.5798 vs heuristic 0.4170 (real recovered labels) | ✅ complete (diagnostic-level) |
| Vector retrieval | 934 chunks; query | BGE-768 embed (GPU) → cosine store → topic-boost rerank | store + ranked hits | `src/retrieval/*` | index build 6.24 s; search spot-checks | ✅ complete |
| Evidence graph | all artifacts | typed nodes/edges; resolve-or-raise | `evidence_graph.json` (6063/17949) | `src/graph/*` | build run + resolve CLI + tests | ✅ complete |
| VLM clip summaries | 20 clips | frozen Qwen2.5-VL-3B, 8 frames @≤448², greedy JSON | `video_summaries.parquet` | `src/vision/*` | run log: 20/20 `vlm`, mean conf 0.95, 492 s | ✅ complete |
| Temporal grounding | all of the above | per-window AlignedTuple; resolution + chronology enforced | `aligned_tuples.parquet` (3399) + run record | `src/temporal/grounding.py` | this session: resolution 1.0, 0 violations, 20 VLM clips embedded, 3 VideoClip contract validations | ✅ complete |
| Workbench UI | artifacts | shared playback clock; live charts; live retrieval; export | localhost:8501 | `streamlit_app.py`, `src/ui/*` | healthz 200; 3 AppTest render tests | ✅ complete |
| Explanation generation | — | — | — | — | Not found in current codebase evidence | ❌ Phase 11 |
| Fusion / evidence selection | — | — | — | — | Not found | ❌ Phases 9–10 |
| Real KPI eval on system outputs | fixtures only | `src/eval/` harness | fixture metrics | `src/eval/run.py` | oracle fixture run | ◐ Phase 12 |

## Explicitly demo / stubbed / weak (all visibly labeled in-product)

1. **AI CLAIMS timeline row + claim-verification statuses** — demo-badged
   (`src/ui/workbench.py::claim_events`, `build_claim_rows`) until Phase 11.
2. **Header Confidence / Hallucination-risk chips** — demo-badged.
3. **SOP-card match-%** for build-time linked chunks — stable hash placeholder,
   demo-badged (`build_sop_cards`); the *live retrieval* scores are real.
4. **Failure/severity labels** — weak deterministic scaffolding
   (`assemble_incidents.LabelDeriver.weak_*`; `manifest.json label_status`);
   the recovered good/bad run labels (`docs/_data/quality_labels.jsonl`) are
   real but run-level.
5. **Video↔incident sync** — constructed (label-matched), never presented as
   measured; caveat embedded in clip_summaries, tooltips, run records (I-8).
6. **`verify_llm.py`** — placeholder judge by design (module docstring).
7. **AUROC/ECE in `src/eval/metrics.py`** — documented fixture placeholders
   (lines 148–149, 199–201) pending Phase 12.
