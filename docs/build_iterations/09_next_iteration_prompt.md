# Next Iteration Prompt

```text
Continue from docs/context/ and docs/build_iterations/. The pending task pass is
complete on branch codex/complete-pending-phases: text dry-run is bounded,
Recipe A evaluation is PASS over weak deterministic labels, browser smoke exists,
and TGFX T-02/T-03 Recipe A artifact substrate is generated via
scripts/build_dataset.py.

First re-run baseline checks, then implement the next smallest DAG task:
curated TGFX validation fixtures plus evidence graph resolution. Preserve Recipe
A behavior, do not treat weak labels as ground truth, do not read test split
inside training/model code, and update docs/context/ after validation.
```
