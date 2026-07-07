# Open Requirements

| Requirement ID | Description | Priority | Current Status | Acceptance Criteria | Dependencies | Blocking Issues | Planned Iteration |
|---|---|---:|---|---|---|---|---|
| REQ-CLI-001 | Provide CLI orchestration for ETL and evaluation | High | Complete | `python -m src.cli --help` lists stage commands; tests pass | Typer, config, ETL modules | None current | Maintenance |
| REQ-SENS-001 | Build sensor incident windows from configured raw sensor data | High | Complete for current implementation | Sensor tests pass; current sensor artifact has 1702 rows | pandas/numpy, config, schemas | Coverage gaps remain | Maintenance |
| REQ-TEXT-001 | Build text chunks from SOP/maintenance manuals | High | Complete for current implementation | Tests pass and artifact exists; dry-run completes with bounded PDF pages | tiktoken/pypdf/python-docx, config | large manuals still take about 35s for two docs | Maintenance |
| REQ-VID-001 | Build video index from raw videos and tags | Medium | Complete for current implementation | Video tests pass; ffmpeg available; artifact has 20 rows | ffmpeg/ffprobe, config | Browser playback unverified | Maintenance |
| REQ-ASM-001 | Assemble multimodal incident rows | High | Complete for current implementation | `incidents.parquet` exists with 1702 rows; tests pass | sensor/text/video indexes | labels are weak scaffolding | Maintenance plus label-curation iteration |
| REQ-EVAL-001 | Evaluate dataset quality and integrity | High | Complete | Evaluation exits 0 and reports metrics/grade | generated artifacts | Current grade is PASS over weak labels | Maintenance |
| REQ-UI-001 | Provide incident evidence explorer | Medium | Complete for smoke coverage | HTTP smoke passes; helper tests pass; live browser smoke passed | Streamlit, generated artifacts | deeper interaction assertions still optional | Maintenance |
| REQ-DATA-001 | Improve semantic label quality for thesis-ready dataset | High | Partial | Lower unknown labels; improve class entropy and split diversity | data curation, labeling strategy | weak labels are not curated ground truth | Label-curation iteration |
| REQ-DOC-001 | Keep docs current with verified baseline | Medium | Complete for current iteration | README reflects 106 tests and 80% coverage; context docs updated | audit/context docs | none current | Maintenance |
| REQ-SAFE-001 | Checkpoint dirty working tree before refactor | High | Complete for branch checkpoint | Work isolated on `codex/complete-pending-phases` | git/user approval | dirty tree still needs commit/stage decision | Before commit/PR |
| REQ-SEC-001 | Define security/dependency audit baseline if sharing/deploying | Low | Open | Native security check configured or explicitly waived | dependency tooling | No scanner configured | Later hardening |
| REQ-TGFX-001 | Bootstrap TGFX constitution, SDD substrate, and Pydantic contracts | High | Complete for first slice | `CLAUDE.md`, `docs/_sdd/`, `contracts/`, and `tests/contracts/` exist; contract tests pass | master prompt, pydantic | full eval harness deferred | Completed iteration |
| REQ-TGFX-002 | Implement TGFX frozen evaluation harness and metric meta-tests | High | Complete for fixture/meta-test seed | `src/eval/`, `tests/eval_meta/`, and executable fixture checks exist and pass | TGFX contracts, feature path | real-data eval still future work | Completed iteration |
| REQ-TGFX-003 | Implement TGFX dataset loaders, manifest, alignment ledger, and split scaffolding | High | Complete for Recipe A artifact substrate | `scripts/build_dataset.py`, `docs/_data/manifest.json`, `docs/_data/alignment_ledger.jsonl`, and `data/splits/*.jsonl` are generated from processed artifacts | TGFX contracts, eval harness | curated TGFX gold labels still pending | Completed iteration |

Unknown:
- Final publication/distribution requirements are Unknown; raw data licensing/provenance must be verified before release.
