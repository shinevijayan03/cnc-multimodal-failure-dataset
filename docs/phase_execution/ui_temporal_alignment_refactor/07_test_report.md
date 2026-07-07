# 07 — Test Report

## Test-requirement coverage (spec items 1–10)

| # | Required test | Implemented as | Level |
|---|---|---|---|
| 1 | Timeline renders all required rows | `test_timeline_renders_all_required_rows` (rows == SENSOR/VIDEO/SOP/AI CLAIMS/NOTES) | unit |
| 2 | Event bars render with correct labels | `test_event_bars_have_labels_spans_and_provenance` (labels, ordered spans, axis bounds, demo badging) | unit |
| 3 | Play-through changes current time | `test_play_through_advances_current_time` (+rate scaling); `test_play_then_stop_toggles_shared_state` | unit + AppTest |
| 4 | Stop pauses playback | `test_stop_pauses_playback` (tick while stopped is a no-op); AppTest stop click | unit + AppTest |
| 5 | Timeline cursor is visible | cursor rule layered in `_timeline_chart`; `test_cursor_active_flags_in_events_frame` verifies the cursor's active-set semantics | unit (+ render via AppTest) |
| 6 | Video time and shared time synchronized where testable | `test_video_offset_tracks_shared_time_proportionally` (midpoint→half clip, end→full clip, degenerate-safe) | unit |
| 7 | Sensor chart receives current time/cursor | sensor fragment reads shared state; AppTest scrub test asserts `wb_current` follows the slider | AppTest |
| 8 | Export report contains metadata and evidence | `test_export_report_contains_metadata_events_and_claims` (id, failure, axis+cursor, all events, explanation, claims, provenance note) | unit |
| 9 | Existing incident page still renders | `test_workbench_renders_without_exception` (real app + real data, selector populated) | AppTest |
| 10 | No regression in data loading | full suite green incl. untouched `test_incident_explorer.py` (9 tests) | unit |

Additional: `test_sensor_baseline_is_complement_of_evidence`,
`test_playback_stops_at_end_and_replays_from_start`, `test_seek_clamps_to_axis`,
`test_ai_explanation_grounded_in_real_span`, `test_claim_rows_mark_unverified_demo_claims`.

## Browser-level testing

Playwright is not installed in this environment (import fails), so per the
spec's fallback rule the browser smoke remains **opt-in**
(`RUN_BROWSER_SMOKE=1` + `pip install playwright`), updated for the new
workbench texts. The in-process `streamlit.testing.v1.AppTest` harness covers
render + interaction without a browser and runs in the default suite.

## Results

```text
tests/unit/test_workbench.py .............   12 passed (0.55s)
tests/ui/test_workbench_apptest.py ...        3 passed (4.96s)
full suite                                  136 passed, 1 skipped (17.37s)
ruff                                        All checks passed
```

Suite delta: 121 → 136 tests (+15), zero pre-existing tests broken or modified
except the browser smoke text update.
