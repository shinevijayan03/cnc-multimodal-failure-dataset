# 06 — V&V Loop Report

## Loop UI.1

- **Observation:** Video clip duration was hacked from a leftover expression
  (`incident.get("video_fps") and 0.0 or 0.0`) and a session-state default.
- **Evidence:** self-review of first `streamlit_app.py` draft.
- **Root Cause Hypothesis:** drafted before deciding where duration lives;
  the incident row has no `duration_s`, but `video_index.parquet` does.
- **Fix Applied:** `_clip_duration()` looks up `duration_s` from
  `tables.video_index` by `video_file`, 7.0 s fallback.
- **Validation Command:** `pytest tests/ui/test_workbench_apptest.py -q`
- **Validation Result:** 3 passed (render path exercises the lookup).
- **Regression Risk:** none (new helper, no shared code touched).
- **Exit Decision:** continue.

## Loop UI.2

- **Observation:** `use_container_width=True` used for Altair charts while the
  rest of the file uses the newer `width="stretch"` API.
- **Evidence:** grep of draft; existing code style.
- **Root Cause Hypothesis:** muscle-memory API; deprecated param.
- **Fix Applied:** replaced all occurrences with `width="stretch"`.
- **Validation Command:** full `pytest -q` + app healthz.
- **Validation Result:** 136 passed; healthz 200; no deprecation warnings in
  server log.
- **Regression Risk:** none.
- **Exit Decision:** continue.

## Loop UI.3

- **Observation:** "Jump to event" selectbox key persists across incident
  switches; a stale event id from the previous incident could linger.
- **Evidence:** design review of `_init_playback`.
- **Root Cause Hypothesis:** widget keys survive reruns unless cleared.
- **Fix Applied:** `_init_playback` pops `wb_jump` (and `wb_slider`) when the
  selected incident changes.
- **Validation Command:** AppTest render + scrub test (state reset path runs
  on first render).
- **Validation Result:** 3 passed; no exception.
- **Regression Risk:** low (reset only on incident change).
- **Exit Decision:** continue.

## Loop UI.4

- **Observation:** unused `field` import in `workbench.py` draft; unused
  `asdict` in `windows.py` had bitten before.
- **Evidence:** self-review before running ruff.
- **Fix Applied:** import removed.
- **Validation Command:** `ruff check ...`
- **Validation Result:** All checks passed.
- **Exit Decision:** continue.

## Critical-bug checklist (must all be clear before exit)

| Critical bug | Status |
|---|---|
| Video and sensor cursor not aligned | Clear — single shared `wb_current`; offset mapping unit-tested |
| App fails to start | Clear — healthz 200, log clean |
| Timeline not visible | Clear — fragment renders; AppTest exercises it |
| Incident data no longer loads | Clear — AppTest selector populated; 9 explorer tests green |
| Export button crashes | Clear — JSON built before render; content unit-tested |
| Existing core UI disappears | Clear — SOP chunks, alignment table, raw row all preserved |

No open critical bugs. Loop log closed.
