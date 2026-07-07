# Phase 1 — Goal

**Title:** Codebase stabilization and runnable baseline (audit-adjusted scope).

The audit (`docs/architecture_audit/08_runtime_execution_report.md`) classified
the app as RUNS, so Phase 1 shrank to the residual gaps:

1. **Fresh-clone bootstrap** — a new machine with no staged data must be able
   to run the full pipeline (audit risk R-7).
2. **Coverage re-measured** — replace the README-reported 80% with an
   audit-day measurement (audit grounding row 24).
3. **Runbook** — one document with exact commands for sample path, real path,
   tests, and GPU environment.
4. **`.env.example`** — placeholder documenting that no secrets are needed yet
   and which variables model phases will read.
5. **Record gate decisions** — window convention (D10) and GPU-first policy
   (D11) into `docs/_sdd/decisions.md`.
6. **GPU baseline probe** — establish the hardware envelope for Phases 4–11
   and report limitations (user directive: GPU always; report issues).

## Entry criteria (met)

- Audit complete and approved by user 2026-07-03 ("Approved").
- Working tree clean at `9c9733f`.

## Definition of done

- `python scripts/generate_sample_data.py` +
  `python -m src.cli all --config config/dataset.sample.yaml` succeed on a
  machine with no staged data.
- Generator covered by unit tests; full suite green; ruff clean; app starts.
- Runbook + .env.example committed; decisions D10/D11 recorded.
- Coverage measured and reported with the command that produced it.
