# 05 — Self-Evaluation Rubric (applied at the end of every build phase)

Scored 0–5 into `docs/phase_execution/phase_N_rubric_score.md` using:

| Dimension | Score | Evidence | Concern | Required Fix | Confidence |
|---|---|---|---|---|---|

## Dimensions

1. Requirement Fit — phase deliverables match the phase goal doc.
2. Architecture Alignment — matches target interpretation
   (`docs/architecture_audit/04_...md`) and module placement plan.
3. Minimality of Change — smallest safe diff; ≤ ~600 lines/branch (I-11).
4. Code Quality — ruff clean; matches existing idioms (typed config, pure
   numeric cores, atomic writes).
5. Test Coverage — focused tests added; full suite green; meta-tests where
   metrics/verifiers changed.
6. Runtime Executability — app starts; smoke commands pass.
7. Evidence Traceability — every emitted claim/number carries evidence IDs /
   run records (I-2, I-5, I-7).
8. Temporal Grounding Correctness — spans incident-relative, inside [-60,+30],
   chronology validated.
9. Multimodal Consistency — cross-modal outputs agree on IDs, spans, and
   provenance labels.
10. Error Handling — per-item skip+count; typed errors; clean absence paths
    (ffmpeg/GPU/model-weights missing must not crash).
11. Security / Secrets Hygiene — no secrets committed; `.env.example` kept
    current; quarantine respected (I-4).
12. Documentation Quality — phase docs complete; README/runbook updated.
13. Refactor Safety — no contract broken; prior run records still reproducible.
14. User Testability — exact commands provided; sample data available.
15. Definition of Done Completion — phase DoD checklist all checked.

## Scoring scale

```text
0 = missing / broken
1 = very weak
2 = partial
3 = acceptable
4 = strong
5 = excellent
```

## Exit rule

A phase may not exit while any **critical dimension** is below 3:

- Requirement Fit
- Runtime Executability
- Evidence Traceability
- Definition of Done Completion

If a critical dimension cannot reach 3 within the phase, raise a BLOCKED memo
(I-12) at the user gate rather than papering over it.
