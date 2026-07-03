# Open Items and Pending Tasks

## Purpose

Register TODOs, incomplete modules, missing tests, missing docs, missing configuration, UI/GPU gaps, dependency issues, code quality issues, architecture gaps, security gaps, validation gaps, and deployment gaps found during Stage A.

## Open Items Register

| ID | Category | File/Module | Description | Severity | Impact | Recommended Action | Target Phase |
|---|---|---|---|---|---|---|---|
| OI-001 | Documentation drift | `config/dataset.yaml` | Header still says "Phase-1 STUB" and "not yet consumed by code" | Medium | Misleads users because code consumes this config | Refresh comments after approval | Phase 1/2 |
| OI-002 | Open decision | `config/dataset.yaml` | `TODO(review)` for Bosch raw format | Medium | Reader assumptions may be wrong for real data | Confirm `.h5` vs `.csv` raw format with sample files | Phase 2 |
| OI-003 | Open decision | `config/dataset.yaml` | `sensor.output_format` mentions parquet or hdf5 but code writes Parquet only | Medium | Config overpromises HDF5 | Enforce Parquet or implement HDF5 | Phase 2 |
| OI-004 | Open decision | `config/dataset.yaml` | `tokenizer` has TODO review | Low | Text build may use fallback unexpectedly | Document/install `tiktoken` or default whitespace knowingly | Phase 2 |
| OI-005 | Missing raw data | `data_raw` | Raw sensor/video/text data not staged in repo | High | Full build cannot produce `incidents.parquet` | Stage raw data according to README | Phase 6 |
| OI-006 | External tool missing | ffmpeg/ffprobe | `ffmpeg` is not on PATH locally | Medium | Real video normalization cannot run | Install ffmpeg and verify `ffmpeg -version` | Phase 3/6 |
| OI-007 | Optional dependency missing | Environment | `tiktoken`, `pypdf`, and `rank_bm25` are missing locally | Medium | Text/PDF/BM25 behavior may degrade or remain incomplete | Install full requirements or document fallback | Phase 2 |
| OI-008 | Missing UI | Project | No Streamlit app exists | High | User-facing UI requirement unmet | Implement Streamlit UI after approval | Phase 3 |
| OI-009 | Missing GPU abstraction | Project | No compute device utility or GPU-backed feature exists | Medium | GPU requirement unmet where relevant | Add opt-in device utility and GPU path for meaningful workload | Phase 4 |
| OI-010 | Retrieval mismatch | `src/etl/assemble_incidents.py` | Config says `keyword_bm25`; implementation uses topic-overlap ranking | Medium | Scientific docs may overclaim retrieval method | Implement BM25 or rename method to `topic_overlap` | Phase 2 |
| OI-011 | Placeholder/no-op | `src/etl/assemble_incidents.py` | `pass` in topic-relax branch is intentional but opaque | Low | Readability issue | Replace with explicit comment or helper branch | Phase 2 |
| OI-012 | Placeholder assignment | `src/etl/assemble_incidents.py` | `split=Split.train` placeholder before `SplitAssigner` | Low | Could confuse maintainers | Document or create factory flow that assigns split later | Phase 2 |
| OI-013 | Lint | `src/cli.py:88` | Unused local variable `log` | Low | Ruff advisory failure | Remove unused assignment | Phase 2 |
| OI-014 | Lint | `tests/integration/test_integration.py:12` | Unused `pandas` import | Low | Ruff advisory failure | Remove import | Phase 2 |
| OI-015 | Lint | `tests/unit/test_assemble.py:16-17` | Unused `Span` and `Split` imports | Low | Ruff advisory failure | Remove imports | Phase 2 |
| OI-016 | Lint | `tests/unit/test_io_ids.py:7` | Unused `Path` import | Low | Ruff advisory failure | Remove import | Phase 2 |
| OI-017 | Lint | `tests/unit/test_io_ids.py:36` | Unused `src.common.io_utils` import | Low | Ruff advisory failure | Remove import | Phase 2 |
| OI-018 | Lint | `tests/unit/test_video.py:5` | Unused `shutil` import | Low | Ruff advisory failure | Remove import | Phase 2 |
| OI-019 | Lint | `tests/unit/test_video.py:15` | Unused `FfprobeReader` import | Low | Ruff advisory failure | Remove import | Phase 2 |
| OI-020 | Missing UI tests | `tests` | No Streamlit tests because UI is absent | Medium | UI could regress once added | Add UI smoke/service tests | Phase 5 |
| OI-021 | Missing GPU tests | `tests` | No GPU/device tests because GPU path is absent | Medium | GPU fallback could be fragile | Add mocked CPU/GPU tests after utility exists | Phase 5 |
| OI-022 | Docs stale | `docs/implementation_plan.md` | Still says implementation gated on review | Medium | Confuses current status | Refresh or mark historical | Phase 7 |
| OI-023 | Docs stale | `docs/software_design.md` | Says pseudocode is design sketch though code exists | Medium | Confuses reviewers | Refresh current-vs-target language | Phase 7 |
| OI-024 | Docs stale | `docs/architecture.md` | Some "target Phase 2" wording no longer current | Medium | Architecture drift | Refresh after Stage B scope is approved | Phase 7 |
| OI-025 | Logging gap | `src/common/logging_utils.py` | `logs_dir` config exists but logger writes to stderr only | Low | Users may expect log files | Either implement file logs or clarify docs | Phase 2/3 |
| OI-026 | Config gap | `runtime.num_workers` | Worker count is configured but not used | Low | Config overpromises concurrency | Implement parallelism or document as future | Phase 2 |
| OI-027 | Evaluation hardening | `src/evaluate.py` | `pct_malformed_json` is set to 0 after decode path; malformed JSON behavior should be explicit | Medium | Integrity metrics could miss malformed fields if handled inconsistently | Add explicit JSON parse audit and tests | Phase 5 |
| OI-028 | Deployment docs | README/CONTRIBUTING | No Streamlit/GPU setup sections | Medium | New users lack run instructions once features exist | Update docs after implementation | Phase 7 |
| OI-029 | Security/data | `data_raw`, `data_processed` | Gitignore is correct; no secrets found | Low | Need maintain policy | Keep raw/licensed data out of Git | Ongoing |
| OI-030 | Scale validation | Project | Tests use synthetic fixtures only | Medium | Thesis-scale performance and quality unknown | Run real staged data build and evaluation | Phase 6 |

## Summary by Severity

| Severity | Count | Main Themes |
|---|---:|---|
| Critical | 0 | None found |
| High | 2 | Missing raw data, missing Streamlit UI |
| Medium | 18 | Docs/config drift, ffmpeg/deps, GPU, retrieval, tests, validation |
| Low | 10 | Lint, readability, logging/concurrency clarity |

## Immediate Non-Implementation Actions

- Review this register.
- Decide whether Stage B should prioritize UI first, docs cleanup first, or retrieval/GPU work first.
- Stage raw data and install ffmpeg if a real build will be validated soon.
