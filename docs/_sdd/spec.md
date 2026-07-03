# TGFX Spec Substrate

Source of truth:
- `C:/Users/Admin/Downloads/master_prompt.md`.

This file records the implemented repository-local subset of the TGFX spec for
this iteration. It does not replace the full user specification.

## Non-Negotiable Build Order

The master prompt states that the evaluation harness and contract ratchet come
before model code. The current repository-local substrate includes:

1. Repository constitution in `CLAUDE.md`.
2. Decision log in `docs/_sdd/decisions.md`.
3. TGFX contract package in `contracts/`.
4. Contract tests in `tests/contracts/`.
5. Build-iteration evidence in `docs/build_iterations/`.
6. Fixture evaluation harness in `src/eval/` and `tests/eval_meta/`.
7. Recipe A artifact manifest, ledger, and split scaffolding in `src/tgfx/`,
   `scripts/build_dataset.py`, `docs/_data/`, and `data/splits/`.

No model code, training code, VLM code, or learned fusion code is implemented in
this substrate.

## Implemented Contract Scope

Implemented from master prompt section 3:
- `contracts.core.SubCause`
- `contracts.core.WindowPhase`
- `contracts.core.SensorWindow`
- `contracts.core.VideoClip`
- `contracts.core.SOPChunk`
- `contracts.core.TimelineEntry`
- `contracts.core.IncidentTuple`
- `contracts.core.AlignedTuple`
- `contracts.explanation.ChainClaim`
- `contracts.explanation.ExplanationOutput`

## Contract Rules Implemented

| Rule | Implementation |
|---|---|
| Sensor sub-window must be 12.0 seconds | `SensorWindow` validator |
| Sensor sub-window must fit inside [-60.0, +30.0] | `SensorWindow` validator |
| Sensor channels must be exactly `ax`, `ay`, `az` | `SensorWindow` validator |
| Spectral energy must have four bands | `SensorWindow.spectral_energy` field constraints |
| Video sync provenance must be explicit | `VideoClip.sync_provenance` has no default |
| Chain claims require evidence IDs | `ChainClaim.evidence_ids` min length |
| Chain claims must fit inside [-60.0, +30.0] | `ChainClaim` validator |
| Explanation chain must be chronological | `ExplanationOutput` validator |
| Confidence must be between 0 and 1 | `ExplanationOutput.confidence` field constraints |

## Not Yet Implemented

- GBNF grammar generation from `ExplanationOutput`.
- Evidence graph resolution of `evidence_ids`.
- Curated TGFX gold labels beyond weak Recipe A artifact scaffolding.
- TGFX model, encoder, VLM, retrieval, graph, temporal, fusion, explanation, or UI modules.

These are explicitly deferred so that this first iteration remains small and
reviewable.
