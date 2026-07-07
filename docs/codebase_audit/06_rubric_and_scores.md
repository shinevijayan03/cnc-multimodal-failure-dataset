# Rubric and Scores

Scoring:
- 0 = Not present or completely broken
- 1 = Very weak
- 2 = Partially present but unreliable
- 3 = Acceptable baseline
- 4 = Strong
- 5 = Excellent

## Score Summary

| Area | Score | Confidence |
|---|---:|---|
| Repository Understandability | 4 | High |
| Architecture Clarity | 4 | High |
| Runtime Executability | 4 | High |
| Test Coverage and Test Quality | 4 | High |
| Build Reliability | 3 | Medium |
| Code Modularity | 4 | High |
| Error Handling | 3 | Medium |
| Configuration Management | 4 | High |
| Security and Secrets Hygiene | 3 | Medium |
| Data Grounding and Evidence Traceability | 3 | High |
| Documentation Quality | 4 | High |
| Refactor Readiness | 4 | Medium |

Average: 3.67 / 5.

## Detailed Scores

### 1. Repository Understandability

Score: 4

Evidence:
- README has quickstart, status, design doc order, and repo layout.
- Source folders are conventional: `src`, `tests`, `config`, `docs`, `data_pipeline`.
- `pytest --collect-only -q` collected 87 readable test names.

Reason:
- The repo is easy to navigate and has strong documentation, but README test counts are stale.

Risk:
- Documentation drift can mislead future agents.

Fix recommendation:
- Update README status to current test count and coverage after this audit.

Confidence: High.

### 2. Architecture Clarity

Score: 4

Evidence:
- `src/cli.py` has explicit Typer commands.
- ETL modules have clear class boundaries: sensor, text, video, assemble.
- `docs/architecture.md` and `docs/software_design.md` exist.

Reason:
- Architecture is modular and documented. Some runtime mismatch exists around dry-run behavior.

Risk:
- Current docs may not reflect newer Streamlit/UI additions because they are untracked in git status.

Fix recommendation:
- Promote current architecture diagrams and UI module notes into maintained docs after user approval.

Confidence: High.

### 3. Runtime Executability

Score: 4

Evidence:
- Streamlit HTTP check passed with status 200.
- CLI help and evaluation commands passed.
- Required processed artifacts exist.

Reason:
- The app runs and core CLI is usable. Full quick pipeline dry-run timed out on text stage.

Risk:
- New users may hit slow text ETL before reaching a usable dataset build.

Fix recommendation:
- Add a faster text smoke mode or make `--limit` bound work before expensive full-document processing.

Confidence: High.

### 4. Test Coverage and Test Quality

Score: 4

Evidence:
- `87 passed in 45.58s`.
- Total coverage `82%`.
- Tests cover unit, integration, E2E-style demo build, CLI behavior, UI helpers, schemas, and ETL logic.

Reason:
- Coverage and breadth are strong. UI browser behavior is not end-to-end tested.

Risk:
- Streamlit rendering and user interactions could regress despite helper tests.

Fix recommendation:
- Add browser-level smoke tests or Streamlit app testing after refactor boundaries are approved.

Confidence: High.

### 5. Build Reliability

Score: 3

Evidence:
- CI exists and runs install/tests across Python 3.10 to 3.13.
- `python -m compileall -q src streamlit_app.py` passed.
- No native build command is configured in CI.

Reason:
- Test reliability is good, but package build artifact generation is unverified.

Risk:
- Console script packaging could break without CI detection.

Fix recommendation:
- Add a packaging smoke check if distribution matters.

Confidence: Medium.

### 6. Code Modularity

Score: 4

Evidence:
- Clear modules for common utilities, sensor ETL, text ETL, video ETL, assembly, evaluation, and UI helpers.
- `streamlit_app.py` delegates data logic to `src/ui/incident_explorer.py`.

Reason:
- Responsibilities are separated well enough for scoped refactoring.

Risk:
- Cross-module Parquet contracts require careful compatibility testing.

Fix recommendation:
- Define artifact contract tests explicitly before refactoring schemas or IO.

Confidence: High.

### 7. Error Handling

Score: 3

Evidence:
- Custom errors exist in `src/common/errors.py`.
- CLI catches config, assembly, and pipeline errors.
- ETL stages skip unreadable text docs and missing video tools with warnings.
- Text dry-run timeout left a process running.

Reason:
- Error handling is present, but performance/timeouts and long-running stage cancellation are not controlled inside the app.

Risk:
- Long-running operations may appear hung to users.

Fix recommendation:
- Add progress logging and bounded smoke options for heavy stages.

Confidence: Medium.

### 8. Configuration Management

Score: 4

Evidence:
- `config/dataset.yaml` centralizes paths, event detection, video, text, assembly, and runtime options.
- Pydantic config classes validate schema and value ranges.
- Tests cover config loading and invalid inputs.

Reason:
- Strong config structure. Some comments are data-specific and may drift.

Risk:
- Misleading config comments can cause wrong raw-data assumptions.

Fix recommendation:
- Split stable schema docs from dataset-specific run presets.

Confidence: High.

### 9. Security and Secrets Hygiene

Score: 3

Evidence:
- Secret/env scan found no obvious credentials or required env vars.
- No security scanner is configured.
- Raw data and processed artifacts are local files.

Reason:
- No obvious secret risk in code, but no automated dependency/security baseline.

Risk:
- Vulnerable dependencies would not be detected by current CI.

Fix recommendation:
- Add a dependency audit tool if the project will be shared or deployed.

Confidence: Medium.

### 10. Data Grounding and Evidence Traceability

Score: 3

Evidence:
- Evaluation reports check missing files, dangling chunks, duplicate IDs, malformed JSON, and spans.
- Current evaluation reports `pct_unknown_failure=1.0` and `dominant_class_share=1.0`.

Reason:
- Artifact integrity is strong, but semantic label grounding is weak.

Risk:
- Explanations may look evidence-linked while labels remain placeholder/unknown.

Fix recommendation:
- Prioritize label curation and source provenance before downstream modeling claims.

Confidence: High.

### 11. Documentation Quality

Score: 4

Evidence:
- README and multiple design/test/evaluation docs exist.
- `docs/refactor_ecosystem/` contains a broad prior refactor planning set.
- README test count is stale.

Reason:
- Documentation is extensive but needs freshness review.

Risk:
- Stale docs can conflict with verified commands.

Fix recommendation:
- Add a "verified on" section linked to this audit.

Confidence: High.

### 12. Refactor Readiness

Score: 4

Evidence:
- Tests, lint, compile, CLI help, evaluation, and Streamlit smoke pass.
- Architecture is modular.
- Known risks are isolated and documented.

Reason:
- The codebase is ready for scoped refactoring with guardrails, not broad rewrites.

Risk:
- Dirty working tree and untracked source files make ownership ambiguous.

Fix recommendation:
- User should review current git status and decide whether to commit, branch, or isolate current changes before refactoring.

Confidence: Medium.

