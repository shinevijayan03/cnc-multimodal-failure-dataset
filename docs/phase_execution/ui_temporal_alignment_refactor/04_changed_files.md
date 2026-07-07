# 04 — Changed Files

## Created

| File | Purpose | ~Lines |
|---|---|---|
| `src/ui/workbench.py` | Streamlit-free logic: `PlaybackState` (play/stop/seek/tick), `TimelineEvent` + row builders (sensor real spans, derived baseline, demo video/SOP/claims/notes), `events_frame`, `active_events`, `build_ai_explanation`, `build_claim_rows`, `export_report(_json)`, `video_offset_for` | 330 |
| `.streamlit/config.toml` | Dark industrial theme (base dark, amber primary, slate panels) | 12 |
| `tests/unit/test_workbench.py` | 12 unit tests (rows, labels/provenance, baseline complement, play/stop/tick/seek/end-stop, video offset mapping, cursor active flags, export content, grounded explanation, claim statuses) | 160 |
| `tests/ui/test_workbench_apptest.py` | 3 in-process render tests via `streamlit.testing.v1.AppTest`: renders without exception, play→stop toggles shared state, scrub seeks cursor (skip when no staged data) | 75 |
| `docs/phase_execution/ui_temporal_alignment_refactor/*` | This documentation set (00–09) | — |

## Modified

| File | Change |
|---|---|
| `streamlit_app.py` | Full rework: workbench header + export button, playback controls row, video/sensor/evidence grid, two `st.fragment(run_every=0.5s)` live views (sensor chart, timeline), Altair cursor/overlay charts, details expander preserving alignment table + raw row. Cached loaders and all `incident_explorer` imports unchanged. |
| `tests/ui/test_streamlit_browser_smoke.py` | Updated opt-in Playwright assertions to the new workbench texts (header, panels, controls, tabs, export) |

## Untouched (regression safety)

- `src/ui/incident_explorer.py` and its 9 unit tests — all still pass.
- All ETL/eval/contract/feature modules, configs, CLI.
- `tests/unit/test_incident_explorer.py` unchanged and green.
