# Next Prompt

Use this exact prompt to start the next Codex session.

```text
You are continuing work in:

E:\1.Final-Year-Project-2026\4. demo-old\cnc-multimodal-failure-dataset

First read docs/context/ and verify the repo still matches it. The current
checkpoint branch should be codex/complete-pending-phases unless the user has
merged or renamed it.

Current verified state:
- Streamlit app should run at http://localhost:8501.
- Recipe A evaluation currently exits 0 with MVP grade PASS.
- Current labels are weak deterministic scaffolding, not curated semantic
  ground truth.
- TGFX T-01, T-04..T-06, and T-02/T-03 Recipe A artifact substrate exist.
- Generated TGFX substrate files are docs/_data/manifest.json,
  docs/_data/alignment_ledger.jsonl, and data/splits/*.jsonl.

Before changes, run or inspect:
1. git branch --show-current
2. git rev-parse HEAD
3. git status --short
4. python -m src.cli --help
5. pytest -q --cov=src --cov=contracts --cov-report=term-missing
6. ruff check src tests contracts scripts
7. python -m compileall -q src contracts scripts streamlit_app.py
8. python -m src.cli evaluate --config config/dataset.yaml --tier mvp
9. python scripts/build_dataset.py --config config/dataset.yaml
10. HTTP smoke check for http://localhost:8501

Preserve the current architecture:
- Typer CLI in src/cli.py.
- Pydantic config/schema contracts in src/common/.
- ETL modules in src/etl/.
- Local Parquet artifact contracts under data_pipeline/data_processed/.
- Streamlit UI entry point in streamlit_app.py with helper logic in
  src/ui/incident_explorer.py.
- TGFX additive substrate in contracts/, src/eval/, src/features/, src/tgfx/,
  docs/_sdd/, docs/_eval/, docs/_data/, and data/splits/.

Do not:
- Change raw data without approval.
- Change Parquet schema contracts without approval.
- Change ID generation, split assignment, label semantics, or evaluation
  thresholds unless they are the explicit objective.
- Treat weak labels as curated ground truth.
- Revert unrelated user changes.

Recommended next objective:
Harden curated TGFX validation fixtures and evidence graph resolution before
any model/encoder/fusion/decoder work. Keep ETVX and V&V loop reporting, add
guardrail tests first, then update docs/context/ after validation.
```
