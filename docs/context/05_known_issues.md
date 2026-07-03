# Known Issues

## Open Issues

### ISSUE-001: Dirty Working Tree

Description:
- The repository has pre-existing modified and untracked files.

Root cause:
- Unknown. Evidence only shows current git status, not authorship.

Severity:
- High for refactoring.

Current workaround:
- Do not refactor until user chooses a checkpoint strategy.

Proposed fix:
- User reviews `git status --short` and commits, branches, stashes, or explicitly accepts the current dirty state.

Verification required:
- `git status --short` after chosen checkpoint.

Status:
- Open.

### ISSUE-002: Text ETL Dry-Run Still Slow On Large PDFs

Description:
- `python -m src.cli text --config config/dataset.yaml --dry-run --limit 2` now completes, but still takes about 35 seconds on the current staged manuals.

Root cause:
- Inference: likely heavy PDF/manual parsing or tokenization before the limit completes. Evidence: `src/etl/text_etl.py` reads and chunks whole documents; `data_pipeline/data_raw/text_manuals` contains manuals; stage isolation shows text is the timeout stage.

Severity:
- High for ETL developer ergonomics; not currently blocking UI use because processed artifacts exist.

Current workaround:
- Use existing `data_pipeline/data_processed/text_chunks.parquet` for UI/testing; stop orphan Python process if timeout leaves one.

Proposed fix:
- Profile `DocReader.read`, PDF extraction, tokenizer initialization, and chunking; make `--limit` support a fast bounded smoke path.

Verification required:
- `text --dry-run --limit 2` completes under an agreed timeout and leaves no orphan process.

Status:
- Improved; monitor.

### ISSUE-003: Weak Label Scaffolding Is Not Ground Truth

Description:
- Evaluation grade is now `PASS`, but failure/severity/root-cause labels are weak deterministic scaffolding, not curated semantic ground truth.

Root cause:
- Current generated data is not semantically curated enough for final thesis claims. Evidence: manifest label status is `weak_signal_derived_not_ground_truth`; `regime_dist` remains `{'unknown': 1702}`.

Severity:
- High for thesis/final dataset claims.

Current workaround:
- Treat the build as a runnable/demo dataset, not final semantic ground truth.

Proposed fix:
- Curate or derive better labels and validate split/class distributions.

Verification required:
- Curated label provenance exists and evaluation remains healthy without weak-label caveats.

Status:
- Open for curation; demo balance improved.

### ISSUE-004: Deep Browser UI Validation Missing

Description:
- Streamlit HTTP response and a live browser smoke are verified, but deeper incident selection/rendering assertions are not automated by default.

Root cause:
- An opt-in Playwright smoke test exists, but normal local/CI test runs skip it unless `RUN_BROWSER_SMOKE=1`.

Severity:
- Medium.

Current workaround:
- Use helper unit tests, HTTP smoke, live browser smoke, and opt-in Playwright test.

Proposed fix:
- Extend browser smoke to select representative incidents and assert rendered evidence panels.

Verification required:
- Browser smoke test passes.

Status:
- Partially addressed.

### ISSUE-005: README Baseline Drift

Description:
- README status text has been updated for the current baseline: 106 tests passing, 1 opt-in browser smoke skipped, and 80% coverage.

Root cause:
- Documentation not updated after tests/UI/TGFX additions.

Severity:
- Low.

Current workaround:
- Use `docs/codebase_audit/` and `docs/context/` as current verified baseline.

Proposed fix:
- Update README after user approval.

Verification required:
- README values match latest test command output.

Status:
- Closed for current iteration.

### ISSUE-006: TGFX Curated Real-Data Evaluation Harness Not Complete

Description:
- The TGFX fixture evaluation harness and Recipe A artifact substrate exist, but curated real-data fixtures, evidence graph resolution, external judge, and RedTeam probes are not complete.

Root cause:
- T-04..T-06 were implemented as a deterministic fixture/meta-test seed; T-02/T-03 now generates Recipe A artifact manifest/ledger/splits; later tasks must add curated gold data and judge components.

Severity:
- High before model work.

Current workaround:
- Do not implement TGFX model/encoder/fusion/decoder code until dataset substrate and real run records exist.

Proposed fix:
- Implement T-02/T-03 dataset substrate, then harden eval against real validation fixtures and baselines.

Verification required:
- Real validation fixture commands produce expected metrics and append unique run records.

Status:
- Open.

## Closed Issues

None recorded in this context pack.

## Deferred Issues

### ISSUE-D001: Dependency Security Audit Not Configured

Description:
- No native dependency/security scanner is configured.

Root cause:
- Unknown; security scanning may be outside current project scope.

Severity:
- Medium if project is distributed or deployed.

Current workaround:
- No secrets found by source scan; dependencies are declared.

Proposed fix:
- Add dependency audit tooling if sharing/deployment is planned.

Verification required:
- Security/dependency scan command passes or documented waiver exists.

Status:
- Deferred.
