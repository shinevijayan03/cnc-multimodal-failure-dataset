# Current Risks

| Risk ID | Description | Probability | Impact | Mitigation | Contingency | Owner | Status |
|---|---|---|---|---|---|---|---|
| RISK-001 | Dirty working tree causes refactor merge/confusion | Medium | High | Work isolated on `codex/complete-pending-phases` | Commit/stage after user review | User/Codex | Partially mitigated |
| RISK-002 | Text ETL dry-run remains slow on large PDFs | Medium | Medium | Bounded dry-run page cap | Use generated artifact; profile PDF extraction later if needed | Codex | Improved |
| RISK-003 | Current dataset labels are weak scaffolding, not ground truth | High | High | Manifest label caveat and future curation task | Limit claims to demo/readiness, not final semantic quality | User/Codex | Open |
| RISK-004 | Deep UI interaction bugs not caught by smoke tests | Medium | Medium | HTTP, helper tests, opt-in browser smoke, live browser smoke | Manual UI test before demos | Codex | Partially mitigated |
| RISK-005 | README drift misleads next developer | Low | Low | README updated with current baseline | Treat `docs/context/` as current baseline | Codex | Closed |
| RISK-006 | Missing dependency security baseline | Medium | Medium if deployed/shared | Add dependency audit tool | Document waiver if project stays local | User/Codex | Deferred |
| RISK-007 | Raw data licensing/provenance unknown | Medium | High for publication | Build source/license manifest | Do not distribute raw/processed data until verified | User | Open |
| RISK-008 | Packaging path unverified | Low | Low/Medium | Add `python -m build` smoke if distribution needed | Use `python -m src.cli` directly | Codex | Deferred |
| RISK-009 | TGFX curated real-data eval harness is incomplete beyond fixture/meta-test seed and Recipe A substrate | Medium | High | Build curated validation fixtures and evidence graph before model code | Stop model work and harden real validation first | Codex | Open |
