# 00 — Entry Report (Fable audit, 2026-07-03)

| Item | Value | Evidence |
|---|---|---|
| Project root | `e:\1.Final-Year-Project-2026\4. demo-old\cnc-multimodal-failure-dataset` | working directory; `pyproject.toml` present |
| Git branch / HEAD | `codex/complete-pending-phases` @ `cbc57f7` | `git log --oneline -3` |
| Git status at entry | 8 modified + 5 untracked paths — the **uncommitted Build Phase 7 work** (src/vision/, tests/unit/test_vision.py, vision config, grounding/UI wiring, phase docs) plus user-added `AGENTS.md` | `git status --short` captured in this session |
| Tech stack | Python ≥3.10 (runtime 3.12.7, Anaconda); pydantic v2, pandas/pyarrow, numpy/scipy, typer, streamlit 1.54; torch 2.6.0+cu124; transformers 5.1.0; sentence-transformers; networkx 3.6.1 | `pyproject.toml`; version probes run this session |
| Package manager | pip / setuptools (`requirements.txt`, extras in `pyproject.toml`) | `pyproject.toml [project.optional-dependencies]` |
| GPU | NVIDIA RTX 3060, 12 GB, CUDA available | `nvidia-smi`, torch probe (decision D11 baseline) |
| Run commands | `python -m src.cli {sensor,text,video,assemble,all,evaluate}`; `python -m src.tgfx.windows`; `python -m src.tgfx.sensor_features`; `python -m src.encoder.train`; `python -m src.retrieval.{build_index,search}`; `python -m src.graph.evidence_graph`; `python -m src.temporal.grounding`; `python -m src.vision.build_summaries`; `streamlit run streamlit_app.py`; `python scripts/{build_dataset,generate_sample_data,derive_quality_labels}.py` | module `main()` entrypoints; `docs/runbook.md` |
| Test command | `pytest -q` (markers: `ffmpeg`, `browser` opt-in) | `pyproject.toml [tool.pytest.ini_options]` |
| Key configs | `config/dataset.yaml` (real corpus), `config/dataset.sample.yaml` (fresh-clone smoke), `.streamlit/config.toml` (light theme), `.env.example` | files present |
| Docs | README, `docs/runbook.md`, constitution `CLAUDE.md` (+ user copy `AGENTS.md`), decision log `docs/_sdd/decisions.md` (D1–D15), phase records `docs/phase_execution/`, audit/build-plan sets | files present |

## Entry-state findings / blockers

1. **Interrupted session recovered.** The previous session terminated while
   two background jobs ran. Verified outcomes: the Phase 7 VLM summarization
   **had completed** (`video_summaries.parquet`, 20/20 clips, mode `vlm`,
   mean confidence 0.95, 492.4 s total per its log); the Streamlit server had
   died (healthz refused). Recovery actions this audit: regrounded the real
   corpus (3,399 tuples now embed VLM summaries; run record appended) and
   relaunched the app. No production code changed for recovery.
2. **Uncommitted approved work.** Build Phase 7 code/tests/docs are complete
   and test-green but uncommitted (session died before the gate commit).
   Flagged for the post-audit commit.
3. `AGENTS.md` (untracked) is a verbatim copy of the CLAUDE.md constitution —
   user-added for non-Claude agent tools. Not modified.

Entry criteria satisfied — proceeding.
