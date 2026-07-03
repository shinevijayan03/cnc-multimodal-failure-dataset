# Rubric Scorecard

| Area | Score | Evidence | Reason | Required Fix | Confidence |
|---|---:|---|---|---|---|
| Requirement Fit | 4 | pending task pass implemented | Satisfies requested text, labels/splits, browser smoke, README, and TGFX T-02/T-03 substrate | Curated gold labels remain future work | High |
| Minimality of Change | 3 | focused ETL/config/TGFX/doc changes | Changed only needed runtime paths and docs, but generated artifacts changed | Review before commit because tree is large | Medium |
| Code Quality | 4 | pure substrate helpers, ruff pass | Harness/substrate are deterministic and testable | Improve coverage of `src.eval.run` later | High |
| Test Coverage | 4 | `106 passed`, `1 skipped` full suite | Added text, assembly, TGFX substrate, and opt-in UI smoke coverage | Add deeper browser interactions later | Medium |
| Runtime Safety | 4 | fixture CLI runs, HTTP 200, browser smoke | App remains reachable; eval CLI works; substrate generation works | External judge still deferred | High |
| Security Hygiene | 4 | No secrets or credentials added | LLM judge is fixture-only, no API calls | Add secure external judge config later | High |
| Error Handling | 3 | validators and metric parse checks | Invalid outputs reduce schema-valid rate | More explicit CLI error messages later | Medium |
| Backward Compatibility | 4 | full test suite passes | Recipe A schema/ID/raw data contracts preserved | Weak labels need curation before final claims | High |
| Observability | 4 | `docs/_eval/runs.jsonl`, build logs | Run records now append | Add richer run IDs/config hash when real configs land | Medium |
| Maintainability | 4 | Separate eval/feature modules | Future TGFX modules have stable import paths | Avoid duplicating feature math elsewhere | High |
