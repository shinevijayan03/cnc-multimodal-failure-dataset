# 04 — User Review Gates

No phase proceeds to the next without explicit user approval. Ambiguity that
blocks a phase is escalated as a BLOCKED memo with options + recommendation
(constitution I-12) instead of guessing.

## Gate protocol (end of every phase)

1. Run the application (CLI smoke + Streamlit healthz).
2. Write `docs/phase_execution/phase_N_validation_report.md`.
3. Post the review request in this exact format:

```text
PHASE N COMPLETE — USER REVIEW REQUIRED

What changed:
...

How to test:
...

Commands:
...

Expected result:
...

Known limitations:
...

Please test and provide feedback.
I will incorporate your feedback before moving to Phase N+1.
```

4. Wait. Incorporate feedback into `phase_N_feedback_incorporation.md`.
5. Only then open Phase N+1.

## Per-phase user test focus + decisions solicited at each gate

| Gate | User should test | Decision requested |
|---|---|---|
| 1 | Fresh-clone quickstart commands | Approve baseline; **decide window convention (audit R-4)** |
| 2 | Window extraction on a sample incident | Confirm -12..0s default query window |
| 3 | Sensor summary + important interval readability | Approve feature set (4 bands OK?) |
| 4 | Encoder behavior, anomaly scores on val samples | Approve torch/GPU dependency; PatchTST now or later |
| 5 | SOP ingestion + search quality on real manuals | Approve vector-store choice (decision log) |
| 6 | Retrieval quality for known failure scenarios | Approve graph schema |
| 7 | Video workflow; stub vs real VLM output | **Hardware decision: local VLM feasible? (audit R-3)** |
| 8 | Temporal grounding output for sample incidents | Approve tuple content/format |
| 9 | Fusion evidence bundle | Approve correlation baseline scope |
| 10 | Selected top-K evidence sanity | Approve K + confidence presentation; **gold mini-set signoff (R-1)** |
| 11 | Explanation quality on val incidents | Approve decoder model choice + prompt |
| 12 | Faithfulness/eval report | Approve gate thresholds; quarantine guard behavior |
| 13 | Full end-to-end demo | Final acceptance |

## Standing escalation triggers (any phase)

- A needed change would touch `src/eval/` → confirm I-6 process with user first.
- A branch would exceed ~600 changed lines → split and update `docs/_sdd/tasks.md` (I-11).
- Any temptation to read test-split data → stop; it is quarantined (I-4).
- Any pressure to fine-tune the VLM → forbidden in v1 without recorded human
  approval (I-1).
