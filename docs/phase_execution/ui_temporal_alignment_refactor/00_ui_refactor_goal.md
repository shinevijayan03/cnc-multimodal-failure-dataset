# 00 — UI Refactor Goal

Refactor the Streamlit incident explorer into a **dark industrial incident
workbench** with a full temporal-alignment feature set (user spec, 2026-07-03):

1. Temporal Alignment Timeline (rows: SENSOR / VIDEO / SOP / AI CLAIMS / NOTES)
   with colored event bars on the incident-relative time axis.
2. Shared playback state (`currentTimeSec, durationSec, isPlaying,
   playbackRate, selectedEventId`) driving video, sensor cursor, timeline
   cursor, and evidence highlights.
3. Play-through / Stop controls; scrub slider; jump-to-event.
4. Video panel following the shared clock, with event chips.
5. Sensor chart with cursor + evidence-span overlays on the shared axis.
6. Evidence panel tabs: SOP Evidence / AI Explanation / Claim Verification.
7. Export Evidence Report (downloadable JSON, real content).
8. Regression-safe: existing incident selection, SOP rendering, alignment
   table, and raw-row view preserved.
9. Tests for the new behavior.

## Entry criteria (met, recorded)

- Running app process stopped before coding: background task `b9es9bcrf`
  (`python -m streamlit run streamlit_app.py ... --server.port 8501`) stopped
  via the task controller; port 8501 freed. No other app/dev processes were
  running (Phase 2 had no servers).
- Framework detected: **Streamlit** (`streamlit_app.py`, `src/ui/`), no
  React/Node present (`pyproject.toml` has no JS tooling).
- Baseline app ran (healthz 200 verified in the Phase 2 session).

## Reference screenshots note

The message referenced screenshots ("Screenshot 2026-07-03 154015" and target
mocks) but no image files were attached to the session. Implementation follows
the **written spec** (R1–R7), which fully describes the layout, rows, example
events, and behaviors. Flagged for user review.
