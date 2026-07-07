# 05 — Validation Report (2026-07-03)

## Automated checks (commands valid for this repo — Python/Streamlit; no npm)

| Check | Command | Result |
|---|---|---|
| New unit tests | `python -m pytest tests/unit/test_workbench.py -q` | **12 passed** in 0.55s |
| In-process render tests | `python -m pytest tests/ui/test_workbench_apptest.py -q` | **3 passed** in 4.96s (real app file, real staged data) |
| Full suite | `python -m pytest -q` | **136 passed, 1 skipped** in 17.37s (was 121 before refactor; +15, 0 broken) |
| Lint | `ruff check src tests contracts scripts streamlit_app.py` | All checks passed |
| Byte-compile | `python -m compileall -q streamlit_app.py src/ui` | OK |
| App start | `python -m streamlit run streamlit_app.py --server.headless true --server.port 8501` (background) | Banner printed; `GET /healthz` → **200**; stderr clean |

## Manual smoke validation (spec checklist)

| Item | Result | Evidence |
|---|---|---|
| App starts | ✅ | healthz 200; server log clean |
| Incident page loads | ✅ | AppTest: `test_workbench_renders_without_exception` (selector populated, no exception) |
| Timeline visible | ✅ | timeline fragment renders Altair chart from `events_frame` (AppTest run raises on chart errors; also unit-tested frame content) |
| Play-through advances cursor | ✅ | Unit: `test_play_through_advances_current_time` (incl. 2× rate); AppTest: play click sets `wb_playing=True` and fragment tick path is the same `PlaybackState.tick` |
| Stop pauses cursor | ✅ | Unit: `test_stop_pauses_playback`; AppTest: stop click sets `wb_playing=False` |
| Video and sensor cursor stay aligned | ✅ (by construction) | Both read the single `wb_current` session value; video offset mapping unit-tested (`test_video_offset_tracks_shared_time_proportionally`) |
| Event bars highlight correctly | ✅ | Unit: `test_cursor_active_flags_in_events_frame` (active set == `active_events`) |
| Export report works | ✅ | `st.download_button` serves real JSON; content unit-tested (`test_export_report_contains_metadata_events_and_claims`) — no faked success |
| Existing incident selection works | ✅ | AppTest selector populated; `main_incident_selector` key unchanged |
| Existing evidence/SOP content renders | ✅ | SOP tab reuses `incident_text_evidence` (untouched, unit-tested); alignment table + raw row preserved in details expander |

## Runtime status

```text
RUNS — http://localhost:8501 (healthz 200), dark workbench renders,
136-test suite green, no regressions.
```

## Numbers provenance

All counts above trace to the commands in the first table (I-7). No model
metrics were produced; no run record required.
