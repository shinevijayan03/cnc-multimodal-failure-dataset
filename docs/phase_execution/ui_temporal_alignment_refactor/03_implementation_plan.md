# 03 — Implementation Plan (as executed)

Team roles applied: UI architect (layout/state design), senior frontend
engineer (Streamlit/Altair implementation), test engineer (unit + AppTest
harness), V&V loop controller (loop log in 06).

## Design decisions

1. **Split logic from rendering.** All new behavior lives in a Streamlit-free
   module `src/ui/workbench.py` (playback state machine, timeline event
   builders, explanation/claims, export) so it is unit-testable without a
   browser. `streamlit_app.py` only renders.
2. **Shared clock = fragment.** One `st.fragment(run_every=0.5s)` advances
   `PlaybackState` by wall-clock delta × rate and re-renders the sensor chart
   and timeline (the two cursor views). Controls outside the fragment mutate
   the same session state and trigger full reruns.
3. **Video follows, never leads.** `st.video` cannot emit its position, so the
   shared clock is master: on rerun the video gets `start_time` = proportional
   clip offset and `autoplay` while playing. Documented in-UI as best-effort
   (sync provenance is 'constructed' anyway — I-8).
4. **Altair for both charts** (already a Streamlit dependency — no new deps):
   layered line + rect(evidence spans) + rule(cursor) for the sensor panel;
   Gantt bars + text labels + rule(cursor) for the timeline, row order fixed
   to SENSOR/VIDEO/SOP/AI CLAIMS/NOTES, active bars at full opacity.
5. **Dark industrial theme** via `.streamlit/config.toml` (`base="dark"`,
   amber primary, slate backgrounds) + a small CSS block for header chips and
   panel titles.
6. **Provenance-honest demo data.** Only `sensor_relevant_spans` carries real
   timing today. Video/SOP/claims/notes bars are demo-badged placeholders
   built per the spec's example pattern, scaled onto the real axis, each with
   a `detail` string naming the build phase that will make them real.
7. **Preserve everything that worked.** `src/ui/incident_explorer.py` is
   untouched; sidebar, incident selector, SOP chunk rendering, alignment
   table, and raw-row view all survive (alignment/raw moved into a details
   expander).

## Work sequence

1. Stop running server (task b9es9bcrf) ✅
2. `src/ui/workbench.py` — state machine + event builders + export ✅
3. `.streamlit/config.toml` dark theme ✅
4. `streamlit_app.py` rework (header, controls, grid, fragments, timeline,
   details) ✅
5. Tests: 12 unit tests (`tests/unit/test_workbench.py`), 3 in-process render
   tests (`tests/ui/test_workbench_apptest.py` via `streamlit.testing.v1`),
   browser smoke updated for new texts (still opt-in) ✅
6. Full suite + ruff + live server + docs ✅

## Explicitly out of scope (future phases)

- Real video events (Phase 7 VLM), real SOP time anchors (Phase 8), real AI
  claims + verification (Phases 11–12), user note persistence, click-on-bar
  seeking (Altair selection → seek; `st.altair_chart(on_select=...)` noted as
  a follow-up), custom JS video component for true bidirectional sync.
