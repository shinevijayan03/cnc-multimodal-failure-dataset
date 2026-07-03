# Markdown Refactoring Plan

## Purpose

Plan how to refresh and standardize project Markdown after Stage A approval, without changing source behavior before review.

## Current Markdown Files

| File | Current Role | Stage A Finding | Refactor Action After Approval |
|---|---|---|---|
| `README.md` | Main user quickstart | Useful and mostly current, but lacks Streamlit/GPU notes | Add UI/GPU sections after implementation; link Stage A docs |
| `CONTRIBUTING.md` | Developer setup | Useful; lacks Streamlit/GPU/dev diagnostics | Add ffmpeg, optional deps, UI, GPU, lint notes |
| `docs/recipe_a_overview.md` | Conceptual overview | Strong but marked Phase 1 design | Re-label current vs target; resolve open questions that are already implemented |
| `docs/implementation_plan.md` | Original phased plan | Still says implementation gated despite implemented code | Convert to historical plan or current roadmap |
| `docs/architecture.md` | Existing architecture | Good but partly stale | Update with implemented source facts and new diagrams |
| `docs/software_design.md` | Existing design doc | Good but contains design sketches now implemented | Refresh as current design plus future extensions |
| `docs/test_strategy_and_plan.md` | Testing strategy | Strong but not updated with 76 passing tests | Add current verification results and UI/GPU gaps |
| `docs/test_cases.md` | Test case catalog | Aligns well with tests | Add UI/GPU planned test IDs after implementation |
| `docs/evaluation_criteria.md` | Dataset quality criteria | Still relevant | Add actual report command/status and known data blockers |

## Refactoring Principles

- Preserve useful existing content.
- Do not claim Streamlit or GPU capabilities until implemented.
- Mark sections explicitly as Current or Target.
- Keep run commands accurate and tested.
- Add troubleshooting for missing raw data, missing ffmpeg, missing optional text dependencies, and missing `incidents.parquet`.
- Use one navigation table in README pointing to current docs.
- Avoid duplicating the same architecture explanation across every document.

## README Target Structure

```markdown
# CNC Multimodal Failure-Explanation Dataset Pipeline

## Purpose
## Current Status
## Repository Layout
## Prerequisites
## Installation
## Raw Data Staging
## Configuration
## Run the Pipeline
## Run Evaluation
## Streamlit UI
## GPU Support
## Testing
## Troubleshooting
## Known Limitations
## Next Steps
```

## Documentation Navigation Target

Add a concise table:

| Need | Document |
|---|---|
| Understand the pipeline | `docs/recipe_a_overview.md` |
| See architecture | `docs/architecture.md` and `docs/refactor_ecosystem/03_ARCHITECTURE_DOCUMENT.md` |
| See software design | `docs/software_design.md` and `docs/refactor_ecosystem/04_SOFTWARE_DESIGN_DOCUMENT.md` |
| Run tests | `docs/test_strategy_and_plan.md` |
| Review Stage A plan | `docs/refactor_ecosystem/00_EXECUTION_SUMMARY.md` |

## Specific Fixes

| ID | File | Fix |
|---|---|---|
| MD-01 | `config/dataset.yaml` comments | Remove "Phase-1 STUB" wording and say config is consumed by code |
| MD-02 | `docs/implementation_plan.md` | Mark completed phases and remaining Phase 3 scale/validation work |
| MD-03 | `docs/architecture.md` | Replace "target Phase 2" wording with current implementation notes |
| MD-04 | `docs/software_design.md` | Replace pseudocode framing with implemented design framing |
| MD-05 | `README.md` | Add ffmpeg missing behavior and optional dependency behavior |
| MD-06 | `README.md` | Add Streamlit section after UI exists |
| MD-07 | `README.md` | Add GPU section after device utility exists |
| MD-08 | `CONTRIBUTING.md` | Add lint command and current ruff status |
| MD-09 | `docs/test_strategy_and_plan.md` | Add current `76 passed` verification and UI/GPU test gaps |

## Approval Boundary

Stage A created this plan only. Existing Markdown files should be updated in Stage B after approval.
