# Validation Matrix

## Purpose

Map requirements to validation methods, test cases, evidence artifacts, and current status.

| Requirement | Validation Method | Test Case | Evidence Artifact | Status |
|---|---|---|---|---|
| Load typed config | pytest | UT-CFG-01..06 | Test suite output | Passed |
| Resolve repo-relative paths | pytest | UT-CFG-02 | Test suite output | Passed |
| Validate schema rows | pytest | UT-SCH-01..05 | Test suite output | Passed |
| Atomic Parquet write | pytest | UT-IO-01..02 | Test suite output | Passed |
| Deterministic IDs | pytest | UT-ID-01..02 | Test suite output | Passed |
| Sensor normalization | pytest | UT-SENS-01..03 | Test suite output | Passed |
| Sampling-rate estimation | pytest | UT-SENS-04..06 | Test suite output | Passed |
| Event detection | pytest | UT-SENS-07..11 | Test suite output | Passed |
| Window carving and spans | pytest | UT-SENS-12..15 | Test suite output | Passed |
| Text chunking | pytest | UT-TEXT-01..04 | Test suite output | Passed |
| Text fallback/token counts | pytest | UT-TEXT-05 | Test suite output | Passed |
| Topic tagging | pytest | UT-TEXT-06..07 | Test suite output | Passed |
| Video probe/ffmpeg wrappers | pytest | UT-VID-01..05 | Test suite output | Passed |
| Video tag merge | pytest | UT-VID-06..07 | Test suite output | Passed |
| Assembly matching/retrieval/splits | pytest | UT-ASM-01..12 | Test suite output | Passed |
| Stage integration | pytest | IT-SENS, IT-TEXT, IT-ASM | Test suite output | Passed |
| Evaluation metrics | pytest | IT-EVAL-01..02 | Test suite output | Passed |
| CLI commands | pytest and CLI help | UT-CLI-01..03, CLI help | Test suite and command output | Passed |
| Full synthetic e2e | pytest | E2E-01..02 | Test suite output | Passed |
| Real raw-data build | Manual/acceptance | ACC-02 | `incidents.parquet` | Blocked: raw data not staged |
| Real video normalization | Manual/integration | E2E-VID-01/ACC-02 | `video_index.parquet` and clips | Blocked: ffmpeg missing |
| Streamlit UI | UI test/manual | UT-UI/IT-UI/ACC-04 | UI launch evidence | Not implemented |
| GPU abstraction | Unit/integration | UT-GPU/IT-GPU | Device metadata | Not implemented |
| PyTorch GPU available | Environment check | IT-GPU-01 | GPU environment report | Passed locally |
| TensorFlow GPU available | Environment check | IT-GPU-01 | GPU environment report | Not available |
| Docs current with code | Review | UT-MD-01/ACC-01 | Updated README/docs | Planned |
| Lint clean | ruff | LINT-01 | Ruff output | Failed: 8 findings |
| Optional text dependencies installed | Import check | DIAG-02 | Dependency inventory | Partial: some missing |
| BM25 retrieval behavior | Unit/review | UT-RET-01 | Retrieval tests/docs | Planned |
