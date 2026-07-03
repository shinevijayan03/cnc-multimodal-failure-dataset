# Phased Implementation Roadmap

## Phase 0 - Repository Discovery

Goal:

- Understand current state.

Outputs:

- Inventory
- Module map
- Dependency map
- Initial risk register

Stage A status:

- Complete.

## Phase 1 - Documentation and Design

Goal:

- Produce complete documentation ecosystem.

Outputs:

- Architecture document
- Software design document
- Testing plan
- Validation plan
- Streamlit UI plan
- GPU plan
- Open-items register

Approval gate:

- Stop and wait for human approval.

Stage A status:

- Complete; awaiting approval.

## Phase 2 - Safe Refactoring Foundation

Goal:

- Refactor code/config/docs without changing behavior.

Actions:

- Fix advisory lint findings.
- Improve naming/comments.
- Centralize shared runner/diagnostics if UI is approved.
- Add stricter config validation.
- Resolve config/docs drift.
- Decide retrieval method alignment.
- Improve logging/error display where needed.

Expected outputs:

- Lint-clean source/tests.
- Updated config comments.
- Shared runner/diagnostics services if approved.

## Phase 3 - Streamlit UI Implementation

Goal:

- Build local Streamlit interface.

Actions:

- Add Streamlit dependency.
- Create UI app.
- Connect backend services.
- Add user controls.
- Add status and results views.
- Add diagnostics and error handling.

Expected outputs:

- `streamlit_app.py` or `src/ui/streamlit_app.py`
- UI service tests
- README run command

## Phase 4 - GPU Enablement

Goal:

- Add GPU acceleration where useful.

Actions:

- Add device detection.
- Add CPU fallback.
- Add config/UI toggle.
- Add GPU logging.
- Add performance benchmark.
- Apply GPU only to approved workloads such as embeddings/retrieval.

Expected outputs:

- Device utility
- GPU tests
- Benchmark notes

## Phase 5 - Test Implementation

Goal:

- Add missing tests.

Actions:

- Unit tests.
- Integration tests.
- Streamlit tests.
- GPU tests.
- Regression tests.

Expected outputs:

- Expanded pytest suite
- Passing CI-friendly commands

## Phase 6 - Integration Validation

Goal:

- Validate end-to-end behavior.

Actions:

- Run full workflows on staged raw data.
- Validate outputs.
- Compare expected vs actual metrics.
- Capture logs and evidence.
- Verify ffmpeg video path if installed.

Expected outputs:

- `incidents.parquet`
- `eval_report.json`
- `eval_report.md`
- Validation notes

## Phase 7 - Documentation Finalization

Goal:

- Update all docs to reflect final implementation.

Actions:

- Update README.
- Update architecture.
- Update software design.
- Update run instructions.
- Update test instructions.
- Update troubleshooting.

Expected outputs:

- Current, navigable documentation.

## Phase 8 - Final Completion

Goal:

- Deliver a complete, tested, documented solution.

Actions:

- Run all tests.
- Run Streamlit app.
- Validate GPU path if implemented.
- Validate CPU fallback.
- Produce final summary.

Final acceptance criteria:

- Code passes tests.
- UI launches.
- Docs match behavior.
- Pipeline builds on staged data.
- Evaluation report exists.
- Remaining open items are documented future work.
