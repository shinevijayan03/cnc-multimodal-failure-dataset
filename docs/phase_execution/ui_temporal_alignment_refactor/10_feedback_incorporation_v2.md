# 10 — Feedback Incorporation v2 (2026-07-03)

User feedback on the first workbench iteration, with reference screenshots of
a simulated target UI (4 dark shots) plus the original light explorer shot.

| Feedback | Incorporation |
|---|---|
| "the vibration sensor timeline and video playback time is not aligned in the ui" | **Root cause:** v1 mixed three axes (video 0..clip-s, sensor −8..+8 s, timeline −8..+8 s). **Fix:** one unified 0-based incident axis (`incident_axis()` in `src/ui/workbench.py`); video transport now displays the shared clock (`Xs / Ds`), the sensor chart x-axis, live readout `t = Xs`, and the timeline cursor all show the same number, exactly like the reference shots. |
| "refactor the current ui to behave exactly like in the shots" | Rebuilt all three panels to the reference design: `● MACHINE VIDEO STREAM` header + CAM meta + time-chips that highlight at the cursor + transport row (step ↞ ▶ ↠, slider, `Xs / Ys`, rate, ⤢ Snapshot); `SENSOR TIME-SERIES` with channel pills, smooth RMS curves (via the one feature path, I-3), shaded labeled anomaly regions, dashed THRESH rules, cyan cursor + dot, live readouts with red **ANOMALY** badges; `SOP EVIDENCE & EXPLANATION` match-% cards with Matched/Partially Matched badges and matched-phrase chips; `TEMPORAL ALIGNMENT TIMELINE` with per-event colors (teal/violet/amber/red), labels inside outlined bars, and Play-through / Stop / Export in the timeline header. |
| "make the color white as in the orginal UI, the look and feel as in the screenshot" | Interpreted as **white primary text on the dark industrial background** (the reference shots use white headings/labels with cyan accents); all headings, card titles, and readout values are now white. *If a white background was meant instead, it is a one-line theme flip in `.streamlit/config.toml` — flagged for confirmation.* |
| Tick rate 0.5 s | Kept ("Okay"). |
| Keep demo bars | Kept, still badged `· demo` in tooltips; a **🎬 DEMO simulated incident** selector entry now reproduces the reference scenario exactly (60 s, 5 channels, Vib Anomaly 18–27 s, SOP 4.2/5.7.3/B-12 cards at 94/81/88%). |
| (implicit) Snapshot button in shots | Implemented as a real feature: drops a `source="user"` note on the NOTES timeline row at the current cursor. |

## New/changed behavior summary

- `src/ui/workbench.py` v2: `incident_axis`, `rolling_rms_frame` (imports
  `src.features.vibration.rms` — I-3 single feature path), `live_readouts`
  (baseline mean+3σ anomaly flags), `build_sop_cards` (real chunk ids/tags,
  demo-badged match %), `demo_incident`/`demo_sensor_frame`/
  `demo_timeline_events`/`demo_sop_cards`, per-event colors, user notes,
  `PlaybackState.step`.
- `streamlit_app.py` v2: reference-style panels, unified axis wiring,
  `st.pills` channel toggles, timeline-header controls, details expander.
- Tests: workbench suite grew 12 → 20; AppTest render tests unchanged and
  green. Full suite **144 passed, 1 skipped**; ruff clean.

## Validation delta (supersedes counts in 05/07)

```text
pytest tests/unit/test_workbench.py -q   20 passed
pytest tests/ui -q                        3 passed, 1 skipped (opt-in browser)
pytest -q                               144 passed, 1 skipped
ruff check ... streamlit_app.py          All checks passed
app                                      healthz 200 on :8501
```
