# 09 — User Review Instructions

The app is running at **http://localhost:8501** (restart any time with
`streamlit run streamlit_app.py`).

## Walkthrough (≈5 minutes)

1. **Header** — confirm the dark workbench header shows incident id, equipment,
   window, failure, severity chips, plus `Confidence (demo)` and
   `Hallucination risk (demo)` placeholders, and the **⬇ Export evidence
   report** button.
2. **Play-through** — press **▶ Play-through**. The monospace clock
   (`t = ±SS.ss s`) advances every 0.5 s; the amber cursor moves across the
   sensor chart *and* the timeline in lockstep; the video plays (muted) from
   the mapped offset; bars under the cursor brighten.
3. **Stop** — press **⏹ Stop**. Clock freezes, cursor rules stop, video pauses
   on the next rerun.
4. **Scrub** — drag the *Cursor* slider. Both cursors jump; playback pauses;
   the video reloads at the proportional clip offset.
5. **Rate** — set 2×, play again: the cursor moves twice as fast.
6. **Jump to event** — pick e.g. `SENSOR: Vibration anomaly (evidence span)`;
   the cursor seeks to that bar's start.
7. **Timeline** — verify five rows (SENSOR / VIDEO / SOP / AI CLAIMS / NOTES),
   colored bars with hover tooltips (label, span, source, detail), and the
   `· demo` badges on placeholder bars. The SENSOR anomaly bar is the *real*
   evidence span from the dataset.
8. **Evidence panel tabs** — SOP Evidence (real chunks), AI Explanation
   (grounded sentence citing the real span + demo-badged sentences),
   Claim Verification (table with SUPPORTED span-anchored claim +
   UNVERIFIED demo claims).
9. **Export** — click Export; open the downloaded
   `<incident_id>_evidence_report.json`; check it contains incident metadata,
   the time axis + cursor position, all timeline events with `source`
   provenance, the explanation, and claim statuses.
10. **Regression** — switch incidents in the selector; open the
    *Alignment summary & raw incident row* expander; try the sample corpus by
    pointing the sidebar at `data_pipeline/data_processed_sample`.

## Known limitations to judge with

- Video sync is **one-way and proportional**: the shared clock drives the
  video via start-offset + autoplay; Streamlit's video element cannot report
  its own position back (a custom JS component would be needed for true
  bidirectional sync). The linked clip is label-matched, not time-recorded
  (sync provenance: constructed), so proportional mapping is honest.
- VIDEO/SOP/CLAIMS/NOTES bar *timings* are demo placeholders (badged) until
  Build Phases 7, 8, and 11 produce real ones.
- Clicking directly on a timeline bar does not seek (use *Jump to event*);
  Altair click-to-seek is a noted follow-up.
- Reference screenshots were mentioned but not attached; layout follows the
  written spec — tell me what to adjust visually.

## Feedback wanted

1. Approve the layout/theme, or list visual changes.
2. Is the 0.5 s tick smooth enough, or should it be faster (0.25 s)?
3. Keep the demo bars (badged) or hide rows with no real data yet?
4. Approval to proceed to Build Phase 3 (patching + feature extraction).
