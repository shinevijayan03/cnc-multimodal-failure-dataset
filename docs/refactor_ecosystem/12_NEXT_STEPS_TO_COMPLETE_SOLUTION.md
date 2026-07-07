# Next Steps to Complete the Solution

## Immediate Next Steps

1. Review all Stage A artifacts under `docs/refactor_ecosystem`.
2. Confirm whether the Stage B goal is documentation refresh only, UI implementation, GPU enablement, retrieval cleanup, or all phases.
3. Stage at least a small raw dataset under `data_raw` if a real pipeline build should be validated.
4. Install ffmpeg if video normalization must be exercised locally.
5. Install optional dependencies if full text/PDF/BM25 behavior is expected.

## Phase 1: Documentation and Design Approval

Goal:

- Approve or revise the Stage A findings and plans.

Actions:

- Review `00_EXECUTION_SUMMARY.md`.
- Review `99_REVIEW_AND_APPROVAL_CHECKLIST.md`.
- Decide which open items are in scope for Stage B.
- Confirm the preferred Streamlit app location.
- Confirm whether GPU work should target embeddings/retrieval or remain planned only.

Exit criteria:

- User explicitly approves Stage B.

## Phase 2: Core Refactoring

Goal:

- Clean up safe, low-risk code and configuration drift without changing behavior.

Actions:

- Fix ruff unused import/variable findings.
- Refresh misleading `dataset.yaml` comments.
- Resolve `keyword_bm25` mismatch by either implementing BM25 or renaming the method.
- Add stricter config validation for strategy fields.
- Clarify or remove placeholder/no-op comments.
- Decide whether `logs_dir` and `runtime.num_workers` are current or future features.

Tests:

```bash
python -m pytest -q
python -m ruff check src tests
python -m compileall -q src tests
```

## Phase 3: Streamlit UI Implementation

Goal:

- Add a user-facing local dashboard.

Actions:

- Add Streamlit dependency.
- Add `streamlit_app.py` or `src/ui/streamlit_app.py`.
- Add backend service layer for diagnostics and pipeline execution.
- Add pages/tabs for overview, config, run pipeline, evaluation, outputs, diagnostics.
- Surface missing raw data, missing ffmpeg, optional deps, and output readiness.

Run command:

```bash
streamlit run streamlit_app.py
```

or:

```bash
streamlit run src/ui/streamlit_app.py
```

## Phase 4: GPU Enablement

Goal:

- Add GPU capability only where it provides real value.

Actions:

- Add device utility with CPU fallback.
- Add config/UI flag for `prefer_gpu`.
- Use PyTorch CUDA for embeddings or inference only if such a feature is approved.
- Log selected device and fallback reasons.
- Add benchmark script or report for CPU vs GPU.

## Phase 5: Test Implementation

Goal:

- Cover all newly introduced Stage B behavior.

Actions:

- Add runner/diagnostics tests.
- Add Streamlit import/service smoke tests.
- Add GPU device utility tests with mocked CUDA states.
- Add retrieval strategy tests.
- Add config validation tests for new fields.

## Phase 6: Integration Validation

Goal:

- Validate the complete workflow on staged data.

Actions:

- Run full pipeline on a small real dataset subset.
- Validate generated Parquet outputs.
- Run evaluation report.
- Verify video normalization if ffmpeg is installed.
- Capture evidence artifacts in `data_processed`.

## Phase 7: Final Hardening

Goal:

- Align documentation, commands, and behavior.

Actions:

- Update README.
- Update CONTRIBUTING.
- Refresh `docs/architecture.md`, `docs/software_design.md`, and `docs/implementation_plan.md`.
- Add Streamlit and GPU troubleshooting sections.
- Confirm all commands in docs work.

## Phase 8: Final Completion Checklist

- `python -m pytest -q` passes.
- `python -m ruff check src tests` passes or known exceptions are documented.
- `python -m src.cli --help` works.
- Full pipeline runs on staged data.
- `incidents.parquet` is generated.
- Evaluation report is generated.
- Streamlit app launches.
- GPU path, if implemented, logs selected device and supports CPU fallback.
- Documentation reflects actual behavior.
- Open-items register is reduced to acceptable future work.
