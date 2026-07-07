# 09 — Quality Check Report

All checks executed 2026-07-03 at commit `547f2c1`.

## Automated checks

| Check | Command | Result |
|---|---|---|
| Unit/integration/contract/eval-meta tests | `python -m pytest -q` | 106 passed, 1 skipped (opt-in browser smoke), 8.17s |
| Lint | `ruff check src tests contracts scripts` | All checks passed |
| Byte-compile | `python -m compileall -q src contracts scripts streamlit_app.py` | OK |
| Dataset quality gate | `python -m src.cli evaluate --tier mvp` | GRADE: PASS, zero hard-gate violations |
| CI definition | `.github/workflows/ci.yml` | Present (GitHub Actions); not executed locally — **Unknown** whether current branch is green on CI |

## Code-quality observations (manual review)

**Strengths**
1. Typed config end-to-end: YAML → pydantic `PipelineConfig` (`src/common/config.py`); typos fail at load with exit code 2 (`src/cli.py:37-42`).
2. Closed enum vocabularies at every parquet boundary (`src/common/schemas.py`) — bad labels cannot enter the dataset silently.
3. Pure numeric cores (EventDetector, WindowCarver, Chunker) separated from IO, unit-tested with synthetic inputs — matches its own design doc (`docs/software_design.md`).
4. Atomic parquet writes (`write_parquet_atomic` in `src/common/io_utils.py`) and per-file error tolerance (skip + count, `fail_fast` configurable).
5. Run-record discipline already real: `src/eval/run.py` embeds git_sha, seed, config_hash, dataset_manifest_hash (constitution I-5/I-7).
6. Contracts enforce the constitution mechanically: `evidence_ids min_length=1` (I-2), `sync_provenance` required (I-8), monotone chronology validator.
7. Tests are meaningful: eval meta-tests include corrupted-interval fixtures that must *degrade* metrics (`tests/eval_meta/test_metrics_meta.py`), not just happy paths.

**Weaknesses / debt**
1. **Latent I-3 tension:** RMS math exists in both `src/features/vibration.py` and `src/etl/sensor_etl.py::EventDetector._sliding_rms` (numpy sliding version). Predates the constitution's feature-path rule; must be unified before encoder work.
2. `src/eval/metrics.py` AUROC (line 148–149) and ECE (line 199–201) are documented placeholders — honest but easy to misread in a results table. They are fixture-degenerate, not real statistics.
3. `assemble.text_retrieval.method: keyword_bm25` in config, but retrieval is keyword-topic lookup; `rank-bm25` is an optional dep not exercised. Name overpromises.
4. Two seed regimes (pipeline `random_seed: 1337`; TGFX eval default 20260702). Documented, but a future single `--seed` surface would reduce confusion.
5. `docs/` contains four generations of generated documentation
   (`codebase_audit`, `context`, `build_iterations`, `refactor_ecosystem`) with
   overlapping claims; risk of stale statements being trusted. This audit set
   (`architecture_audit/`) supersedes them for build planning.
6. No `.env.example` / secrets story yet (nothing needs secrets today; decoder/VLM phases will).
7. Coverage: README (verified 2026-07-02) reports 80% with `--cov`; not re-measured today (pytest-cov run not repeated) — treat 80% as **README-reported**, not audit-verified.

## Security / hygiene

- No secrets found in config or code (config is paths + numeric knobs).
- Raw/processed data and archives are gitignored; splits are ID manifests only.
- Test-split quarantine (I-4) is currently **convention + manifest note**, not
  mechanically enforced (nothing prevents `read_parquet` on test rows except
  discipline). Recommend an enforcement helper in the eval-integration phase.

## Documentation quality

- README quickstart commands all verified working today (§08).
- Design docs (architecture, software_design, evaluation_criteria) match the
  code they describe — spot-checked event-detection and chunking sections.
- `docs/_sdd/tasks.md` status table is accurate against the file tree
  (verified: no `src/encoder`, `src/vision`, `src/retrieval`, `src/graph`,
  `src/temporal`, `src/fusion`, `src/explain` exist).
