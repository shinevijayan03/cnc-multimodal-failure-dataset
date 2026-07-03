# Design Plan

## Current State Before Iteration

- TGFX contracts existed in `contracts/`.
- `src/eval/`, `tests/eval_meta/`, and `src/features/` were absent.
- `docs/_eval/gates.yaml` was a placeholder.

## Target State

Add a deterministic eval harness that proves metrics reward oracle outputs and
punish corrupted temporal intervals before model code exists.

## Component Design

| Component | Design |
|---|---|
| `src/features/vibration.py` | Single feature path seed with RMS, variance, kurtosis, relative delta, and rose checks |
| `src/eval/fixtures.py` | Hand-authored oracle fixture plus code-generated corrupted and mixed fixtures |
| `src/eval/metrics.py` | Pure metric functions over `ExplanationOutput` and gold fixture incidents |
| `src/eval/verify_sensor.py` | Deterministic sensor claim verifier importing `src.features.vibration` |
| `src/eval/verify_llm.py` | Fixture-only judge interface placeholder; no external credentials |
| `src/eval/run.py` | CLI entrypoint that prints metrics and appends run records |
| `tests/eval_meta/` | Tests of metric behavior |

## Rollback Plan

Remove `src/eval/`, `src/features/`, and `tests/eval_meta/`; revert
`pyproject.toml`, `docs/_eval/gates.yaml`, `docs/_eval/runs.jsonl`, and
`docs/_sdd/tasks.md` to the previous placeholder state.
