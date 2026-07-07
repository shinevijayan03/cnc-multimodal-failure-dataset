# Risks, Gaps, and Unknowns

| Gap ID | Description | Evidence | Impact | Severity | Recommended Fix | Needed Before Refactoring? |
|---|---|---|---|---|---|---|
| RG-001 | Working tree was dirty before this audit | `git status --short` showed modified source/config/test files and untracked UI/docs/test files | Refactoring could mix audit work with prior user changes | High | User should review/commit/stash or branch current state | Yes |
| RG-002 | `all --dry-run --limit 2` timed out | Command timed out after 124 seconds | Quick smoke path is unreliable | Medium | Add bounded smoke mode or optimize stage ordering | No, but address early |
| RG-003 | `text --dry-run --limit 2` timed out and left a process running | Stage isolation timed out after 64 seconds; PID `38176` stopped | Text ETL may hang or take too long on manuals | High | Profile PDF parsing/tokenization; make `--limit` reduce expensive work predictably | Yes for ETL refactor |
| RG-004 | Dataset evaluation grade is `WARN` | CLI evaluation warnings for class dominance, unknown failure, zero entropy | Semantic labels are not ready for final explanation claims | High | Curate failure/regime labels and improve split diversity | Yes for modeling/data claims |
| RG-005 | README status is stale | README says 76 tests and ~80% coverage; local run found 87 tests and 82% coverage | Users may trust outdated baseline | Low | Update README after user approval | No |
| RG-006 | UI browser interactions not fully tested | Only HTTP 200 was checked; no browser click/screenshot loop | Streamlit page may have interaction/render issues not caught by helper tests | Medium | Add browser or Streamlit UI smoke tests | Before UI refactor |
| RG-007 | Package build unverified | CI does not run `python -m build`; audit did not add build dependency | Console script or wheel packaging could regress unnoticed | Low | Add packaging smoke test if distribution matters | No |
| RG-008 | Security/dependency audit absent | No security scanner in requirements, pyproject, or CI | Vulnerable dependencies may go undetected | Medium | Add dependency audit workflow if shared/deployed | No |
| RG-009 | CI lint is advisory only | `.github/workflows/ci.yml` sets ruff `continue-on-error: true` | Lint regressions can merge | Low | Decide whether lint should block | No |
| RG-010 | Data provenance/licensing not verified in this audit | Raw data source/licensing not validated by commands | Final dataset sharing may be constrained | High | Maintain source/license manifest for raw videos/manuals/sensor data | Yes for publication/distribution |
| RG-011 | Database/API absence is based on negative scan | No DB/API dependencies/routes found, but no formal architecture registry exists | Hidden integrations are unlikely but not impossible | Low | Keep architecture docs current | No |
| RG-012 | Evaluation writes reports during audit | `evaluate` command writes `eval_report.json/md` by design | Audit may update generated processed reports | Low | Treat generated reports as derived artifacts; checkpoint if needed | No |

## Unknowns

1. Unknown: Whether all pre-existing dirty changes are user-approved.
   - Needed to verify: user confirmation or commit history review.

2. Unknown: Whether all Streamlit incident selections render without error.
   - Needed to verify: browser-level test that loads the app, selects representative incidents, and checks for visible errors.

3. Unknown: Whether final raw data licenses allow redistribution.
   - Needed to verify: source URLs, licenses, and local manifest for every raw file.

4. Unknown: Whether package installation via console script `recipe-a` works after wheel build.
   - Needed to verify: package build/install smoke in a clean environment.

5. Unknown: Whether text ETL timeout reproduces on all machines or only this Windows/Anaconda environment.
   - Needed to verify: timed profiling on another environment or CI fixture with representative PDFs.

