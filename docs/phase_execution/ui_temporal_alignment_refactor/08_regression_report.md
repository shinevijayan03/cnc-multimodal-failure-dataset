# 08 — Regression Report

## Protected surfaces and their status

| Surface | Protection | Status |
|---|---|---|
| `src/ui/incident_explorer.py` helpers | **File untouched**; its 9 unit tests unchanged | ✅ all pass |
| Incident selection (`main_incident_selector`) | Same key, same `incident_labels`/`find_incident` path | ✅ AppTest verifies populated selector |
| SOP/maintenance chunk rendering | Reuses `incident_text_evidence` + expander pattern | ✅ renders in SOP tab (AppTest run) |
| Alignment summary table | Preserved verbatim in details expander | ✅ code path unchanged (`alignment_rows`) |
| Raw incident row view | Preserved in details expander | ✅ |
| Sensor plotting helpers (`sensor_plot_frame`, downsampling) | Reused for the Altair chart input | ✅ unit tests unchanged |
| Cached loaders | Same `st.cache_data` functions | ✅ |
| ETL/eval/CLI/pipeline | Zero files touched | ✅ full suite green; `evaluate` unaffected |
| Dataset artifacts | UI is read-only | ✅ |

## Risk notes

1. **Dark theme is app-wide** (`.streamlit/config.toml`): previously the app
   used Streamlit's default (light unless OS-dark). All panels were restyled
   for dark; if the user prefers a theme toggle, config can revert per
   environment. Flagged for review, not a functional regression.
2. **Layout change**: video/sensor/SOP moved from the old "Evidence" tab into
   an always-visible grid; the old "Alignment"/"Raw Row" tabs moved into a
   details expander. All information remains reachable — no content removed.
3. **Fragment reruns every 0.5 s** even while paused (cheap chart re-render;
   Altair over the downsampled frame). No interaction lag observed at 3,000
   points. If the user raises max points to 10,000 the tick cost grows —
   documented as a tuning knob.

## Verification

Full suite before refactor: 121 passed, 1 skipped.
Full suite after refactor: **136 passed, 1 skipped** — every pre-existing test
still green, none modified except the opt-in browser smoke text update.
