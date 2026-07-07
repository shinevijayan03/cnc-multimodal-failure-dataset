# TGFX Constitution - non-negotiable invariants

I-1  FROZEN BACKBONE. The video-language model (Qwen2.5-VL-7B-Instruct primary,
     LLaVA-NeXT-Video comparison) is never fine-tuned in v1. No gradient ever
     touches it. LoRA on the VLM requires all v1 KPI gates green plus explicit
     human approval recorded in docs/_sdd/decisions.md.

I-2  EVIDENCE-OR-SILENCE. Every claim in chronological_evidence_chain MUST carry
     at least one evidence_id that resolves in the evidence graph. Emitting a
     claim with zero resolvable evidence_ids is a schema violation.

I-3  ONE FEATURE PATH. RMS, spectral bands, kurtosis, variance are computed by
     src/features/vibration.py ONLY. Encoder, verifier, and gold-label generator
     import the same functions. Duplicating feature math anywhere violates this
     constitution.

I-4  TEST-SET QUARANTINE. Files under data/splits/test/ are readable ONLY by
     scripts/eval_test.py. No agent reads, prints, greps, or summarizes them.
     Val split drives all iteration.

I-5  DETERMINISM. Every training/eval entrypoint takes --seed; default 20260702.
     Every run record includes git_sha, config_hash, seed, and
     dataset_manifest_hash. A metric without a run record does not exist.

I-6  METRICS ARE CODE-FROZEN. After meta-tests pass, src/eval/ changes require a
     decision-log entry, re-running meta-tests, and re-scoring prior runs.

I-7  NO FABRICATED NUMBERS. Reports, README tables, and dissertation text may
     only contain numbers traceable to a runs.jsonl record. Placeholder tables
     say PENDING(run_id).

I-8  SYNC PROVENANCE DECLARED. Every VideoClip carries sync_provenance. Every
     results table that includes video-derived metrics repeats this caveat.

I-9  CONSTRAINED DECODING. The decoder emits ExplanationOutput via GBNF grammar
     compiled from the JSON Schema. Free-text generation paths exist only in
     baseline B1.

I-10 RATCHET. A branch merges only if contract tests are green, no KPI gate
     regresses on val, and a run record is appended.

I-11 SMALL DIFFS. One task-DAG node per branch. If a task needs more than about
     600 changed lines, split it and update docs/_sdd/tasks.md first.

I-12 BLOCKED BEATS CLEVER. Ambiguity not covered by the Decision Log is
     escalated via a BLOCKED memo with options and a recommendation.
