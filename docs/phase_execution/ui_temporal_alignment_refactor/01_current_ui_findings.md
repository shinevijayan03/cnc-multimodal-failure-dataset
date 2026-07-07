# 01 — Current UI Findings (pre-refactor, commit d3dc5b4)

## Framework & structure

| Aspect | Finding |
|---|---|
| Framework | Streamlit (single page, no routing) |
| Entry | `streamlit_app.py` (~250 lines) |
| Logic layer | `src/ui/incident_explorer.py` — pure, tested helpers (loaders, chunk ordering, plot frames, alignment table) |
| State management | Widget keys only; **no shared playback state of any kind** |
| Styling | Light default theme + small CSS block; not the dark industrial target |
| Tests | 9 pure-helper unit tests + 1 opt-in Playwright smoke |

## What existed

- Sidebar: processed-dir input, refresh, artifact status table.
- Incident selectbox + max-points slider.
- Three tabs: **Evidence** (video / sensor line chart / SOP chunks in three
  columns), **Alignment** (summary table), **Raw Row**.
- `st.line_chart` sensor plot — no cursor, no overlays, no shared axis
  guarantees with video.
- `st.video` — plays independently; no time linkage to anything.

## What was missing vs the target (all confirmed absent)

| Target feature | Status before |
|---|---|
| Temporal alignment timeline | **Missing** (only a static alignment table) |
| Shared playback state | Missing |
| Synchronized video/sensor cursors | Missing |
| Evidence bars by incident-relative time | Missing |
| Play-through / stop controls | Missing |
| Export evidence report | Missing |
| Incident header with severity/confidence chips | Missing (plain caption line) |
| AI explanation / claim verification panels | Missing |
| Dark industrial theme | Missing |

## Reusable assets identified

- All `incident_explorer` helpers (kept unchanged — regression safety).
- `sensor_relevant_spans` on each incident row: **real incident-relative
  evidence spans** — the only real time-anchored evidence available today;
  used as the grounded core of the timeline.
- `video_index.parquet` `duration_s` — used for clip-offset mapping.
- Altair ships with Streamlit — cursor/overlay charts need no new dependency.

## Streamlit platform constraints found

1. `st.video` cannot report its playback position back to Python → true
   bidirectional video sync is impossible without a custom JS component.
   Chosen approach: the shared clock is the master; video follows via
   `start_time` + `autoplay` on rerun (documented in the UI).
2. Continuous cursor advance requires a rerun source → `st.fragment(run_every=0.5)`
   is the supported mechanism (Streamlit ≥1.37; project pins ≥1.54).
