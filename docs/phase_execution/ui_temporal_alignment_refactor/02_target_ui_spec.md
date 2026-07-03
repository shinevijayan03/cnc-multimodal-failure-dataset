# 02 — Target UI Spec (as implemented)

Dark industrial incident workbench, single page, five zones:

```text
┌───────────────────────────────────────────────────────────────────────────┐
│ HEADER  🏭 CNC Incident Workbench · incident <id>                         │
│ chips: Equipment · Dataset · Window · Failure · Severity ·                │
│        Confidence (demo) · Hallucination risk (demo)     [⬇ Export]       │
├───────────────────────────────────────────────────────────────────────────┤
│ CONTROLS  [▶ Play-through] [⏹ Stop] [Rate ×] [Cursor slider] [Jump-to-ev] │
├──────────────┬──────────────────────────────┬─────────────────────────────┤
│ MACHINE      │ SENSOR TIME-SERIES           │ SOP · AI · CLAIMS           │
│ VIDEO STREAM │  · live clock readout        │  tabs:                      │
│  · follows   │  · ax/ay/az lines            │   SOP Evidence (chunks)     │
│    shared    │  · amber evidence-span rects │   AI Explanation (grounded) │
│    clock     │  · amber cursor rule         │   Claim Verification table  │
│  · event     │  (fragment, ticks 0.5 s)     │                             │
│    chips     │                              │                             │
├──────────────┴──────────────────────────────┴─────────────────────────────┤
│ TEMPORAL ALIGNMENT TIMELINE (full width, fragment-ticked)                 │
│  SENSOR    ──────▓▓anomaly▓▓───────── (real spans, amber-highlighted)     │
│  VIDEO     ────normal────wobble──osc──heat── (demo until Phase 7)         │
│  SOP       ────────▓SOP chunk matched▓────── (real ids, demo timing)      │
│  AI CLAIMS ──────▓claim 1 anchored▓──claims── (demo until Phase 11)       │
│  NOTES     ──────────▓engineer flag▓───────── (demo)                      │
│  ── amber cursor rule across all rows ──                                  │
├───────────────────────────────────────────────────────────────────────────┤
│ DETAILS (expander): Alignment summary table · Raw incident row            │
└───────────────────────────────────────────────────────────────────────────┘
```

## Requirement mapping

| Req | Implementation |
|---|---|
| R1 layout | Header chips + 3-column grid + full-width timeline + preserved details |
| R2 timeline | 5 fixed rows, Altair Gantt bars, per-row colors, labels + tooltips, `source` provenance badge (`· demo`, `· derived`) |
| R3 shared state | `PlaybackState` (t0, t1, current_time_s, is_playing, playback_rate, selected_event_id) in `st.session_state`; fragment clock ticks it; scrub/jump seek it; all views read it |
| R4 video | `start_time` = proportional clip offset from shared time; `autoplay` while playing; offset/duration readout; event chips highlight at cursor |
| R5 sensor | Same incident-relative axis (domain locked to [t0, t1]); amber cursor rule; evidence-span rect overlays; channels selectable |
| R6 evidence | Tabs SOP Evidence / AI Explanation / Claim Verification; explanation sentences cite event ids; active-at-cursor caption |
| R7 export | `st.download_button` → JSON with incident metadata, time axis + cursor, all timeline events, explanation, claim statuses, provenance note |

## Time axis convention

The **sensor waveform is the temporal anchor** (matches the existing dataset
contract and decision D10): axis = `t_rel_s` min…max (staged corpus: −8 s…+8 s,
event at 0). All bars, cursors, and exports use incident-relative seconds. The
spec's 0–60 s example events were mapped proportionally onto the real axis.

## Data provenance rules (spec rules 8–10)

- `incident` — read from incidents.parquet (sensor evidence spans, chunk ids).
- `derived` — computed complement (sensor baseline segments).
- `demo` — placeholder timing/labels (video events, SOP timing, claims, notes),
  visibly badged `· demo` in bars, chips, explanation, claims, and the export's
  `provenance_note`. These become real in Build Phases 7 (VLM), 8 (grounding),
  and 11 (decoder).
