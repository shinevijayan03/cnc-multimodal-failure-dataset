# Phase 2 — Goal

**Title:** Windowing convention implementation + sensor evidence IDs (D10).

Operationalize the user-approved window convention so every later phase
(patching, encoder, grounding) consumes one authoritative implementation:

1. Carve **12-second encoder sub-windows, stride 3 s** (D1) from each
   incident's available waveform span, clipped to the [-60, +30] incident
   convention.
2. Resolve the **default [-12s, 0s] query window** (D10) against what each
   recording actually covers — clipped and coverage-recorded, never padded.
3. Mint **`SW_*` sensor evidence IDs** matching the scheme the eval fixtures
   already use (`SW_<incident_id>_<ordinal>`), so encoder outputs will resolve
   in the same ID space the metric harness scores.
4. Persist a `subwindows.parquet` index for both real and sample builds.

## Entry criteria (met)

- Phase 1 approved by user 2026-07-03 ("approved move to next phase").
- D10 recorded in `docs/_sdd/decisions.md`; tree clean at `e53b174`.

## Definition of done

- Pure carving/query functions with unit tests (staged ±8 s span, full
  [-60,+30] span, short-span, clipping, no-overlap cases).
- `python -m src.tgfx.windows --config ...` builds the index for sample and
  real corpora; short spans recorded, not padded.
- Full suite green; ruff clean; `evaluate --tier mvp` still grades PASS (I-10).
