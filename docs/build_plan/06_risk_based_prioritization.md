# 06 — Risk-Based Prioritization

Risks from `docs/architecture_audit/10_risk_register.md`, mapped to the phase
that retires (or permanently caveats) each, ordered by expected damage if
deferred.

| Rank | Risk | Why it outranks others | Retired by | Action if unresolved |
|---|---|---|---|---|
| 1 | R-1 weak labels (circular metrics) | Corrupts every learned component and every accuracy claim in the dissertation | Gold mini-set workstream (Phases 3–6); hard stop before Phase 10 numbers | All accuracy numbers stay PENDING(run_id) with weak-label caveat |
| 2 | R-4 window-convention conflict | Wrong choice forces rework of patching, grounding, and all span metrics | Decision at Phase 1 gate; implemented Phase 2 | BLOCKED memo; Phases 3+ cannot start |
| 3 | R-3 VLM/LLM hardware feasibility | Determines whether Phases 7/11 use real models or stubs; long lead time to change hardware | Feasibility probe at Phase 7 entry (GPU env re-check) | Ship stub mode transparently; thesis reports stub-based pipeline with real-model path documented |
| 4 | R-8 quarantine is honor-system | Single accidental read of test data can invalidate final claims | Phase 12 mechanical guard; discipline until then | Constitution I-4 discipline; audit docs remind every phase |
| 5 | R-2 constructed sync provenance | Permanently limits video temporal claims; cannot be coded away | Never fully retired — caveat machinery (I-8) in Phases 7–8, 12 | Every video-metric table repeats the caveat |
| 6 | R-5 I-3 feature duplication | Cheap now, expensive after encoder lands | Phase 3 refactor + agreement meta-test | Encoder work blocked until unified |
| 7 | R-11 placeholder AUROC/ECE look real | Risk of fabricated-number appearance (I-7 violation in reports) | Phase 12 real implementations | Annotate as placeholder in every surface that prints them |
| 8 | R-6 metric-freeze process cost | Known process tax, not a surprise | Phase 12 batching | Budget extra gate time |
| 9 | R-7 fresh-clone unrunnability | Blocks user testing at every gate | Phase 1 bootstrap | User tests only on the staged machine |
| 10 | R-12 regimes all unknown | Degrades video matching + conditioning, not correctness | Phase 7 (derive or drop decision) | Drop regime conditioning |
| 11 | R-10 scope vs small-diffs | Process risk, managed continuously | Every phase (task-DAG splits) | Update `docs/_sdd/tasks.md` before oversized work |
| 12 | R-9 doc sprawl | Confusion risk only | Superseded by `architecture_audit/` | Link, never copy, older doc sets |

## Prioritization consequences already baked into the roadmap

- The two user decisions with the longest shadows (window convention,
  VLM hardware) are scheduled at the **earliest possible gates** (Phase 1 and
  Phase 7 entry respectively).
- Stub/mock-first design (Phases 7, 11) converts the hardware risk from a
  blocker into a quality tier.
- Gold-set curation runs as a parallel workstream so labeling latency never
  blocks code phases, but gates Phase 10+ reporting.
