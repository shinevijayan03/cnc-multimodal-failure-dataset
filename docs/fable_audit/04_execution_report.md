# 04 — Execution Report (all commands run 2026-07-03 in this session)

| Command | Purpose | Result | Output Summary | Evidence |
|---|---|---|---|---|
| `git status --short`, `git log -3` | entry state | OK | HEAD `cbc57f7`; Phase 7 work uncommitted (session interruption) | entry report |
| `python -m src.vision.build_summaries --config config/dataset.yaml` | Phase 7 VLM run (recovered from interrupted session — first attempt killed for perf, second completed before crash) | **SUCCESS** | 20/20 clips, mode `vlm`, mean confidence 0.95, 492.4 s, ~20 s/clip after the max_pixels fix; VRAM peak ~10.3/12.3 GB | task log `bue08xwu0`; `video_summaries.parquet` |
| `python -m src.temporal.grounding --config config/dataset.yaml` | reground corpus with VLM summaries | **SUCCESS** | 3399 tuples, 1702/1702 incidents, 13,596 evidence ids @ resolution 1.0, 0 chronology violations, `clips_with_vlm_summary: 20`, 3 VideoClip contract validations; run record appended | command output; `docs/_eval/runs.jsonl` |
| `pytest -q` | full test suite | **SUCCESS** | 209 passed, 1 skipped (opt-in browser), 60 s | command output |
| `ruff check …` | lint | **SUCCESS** | All checks passed | command output |
| `python -m src.cli evaluate --tier mvp` | dataset quality gate | **SUCCESS** | GRADE: PASS | command output |
| `python -m streamlit run streamlit_app.py --server.headless true --server.port 8501` (background) | run the application | **SUCCESS** | server up | task `b8heteqas` |
| `GET http://localhost:8501/healthz` | startup verification | **200 OK** | — | probe output |

## Server details

- **Port:** 8501 · **URL:** http://localhost:8501 · startup clean, no errors
  in the server log.
- **Manual review instruction:** open the URL, pick a real incident, press
  ▷ Play-through; verify the VLM summary + label chips under the video, the
  real VIDEO/SOP bars on the timeline, the grounded chronology in the AI
  Explanation tab, the aligned-tuples panel, and ⬇ Export Evidence Report.
  If panels look stale, click the sidebar "Refresh data" button (clears the
  Streamlit cache after the regrounding).

## Process handling

Two stale background tasks from the interrupted previous session were
confirmed dead (no completion records); the port was free. Only
project-related processes were touched at any point.

## Errors encountered and their resolution (full history, this phase)

1. **Slow VLM throughput (first run):** uncapped 720p frames ≈ 10k visual
   tokens/clip → 1–3 min/clip. Killed; processor now caps `max_pixels=448²`
   and the builder logs per-clip progress. Result: ~20 s/clip. (Performance
   fix inside Phase-7 code that was already in flight — not an audit-phase
   production change.)
2. **Benign warnings**, not errors: transformers weight-loading progress bars
   on stderr; `generation flags not valid: ['temperature']` (greedy decoding
   deliberately ignores sampling temperature); torch `pynvml` deprecation
   FutureWarning; `networkx` runpy warning when invoking
   `python -m src.graph.evidence_graph` (module-in-package pattern, harmless).
3. **Session interruption** killed the app server and left Phase 7
   uncommitted; recovery documented in `00_entry_report.md`.
