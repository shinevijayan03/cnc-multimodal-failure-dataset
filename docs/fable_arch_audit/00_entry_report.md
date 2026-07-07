# 00 — Entry Report (fable_prompt Phase 0, 2026-07-03)

| Item | Value |
|---|---|
| Root | `e:\1.Final-Year-Project-2026\4. demo-old\cnc-multimodal-failure-dataset` |
| Git | branch `codex/complete-pending-phases` @ `05761b6`, **clean tree** |
| Stack | Python 3.12 · pydantic v2 · pandas/pyarrow · typer · Streamlit 1.54 · torch 2.6.0+cu124 (RTX 3060 12 GB) · transformers 5.1.0 · sentence-transformers · networkx 3.6.1 |
| Run | `python -m src.cli all/evaluate`; module CLIs: `src.tgfx.windows`, `src.tgfx.sensor_features`, `src.encoder.train`, `src.retrieval.build_index/search`, `src.graph.evidence_graph`, `src.temporal.grounding`, `src.vision.build_summaries`; `streamlit run streamlit_app.py` |
| Test | `pytest -q` → 209 passed, 1 skipped (this session); markers `ffmpeg`, `browser` |
| Build | pip/setuptools; extras `text/retrieval/eval/encoder/dev` (`pyproject.toml`) |
| App entry | `streamlit_app.py` — running now at http://localhost:8501 (healthz 200) |
| Diagrams ingested | 4 user images: (1) system overview, (2) grounding+decoder pipeline, (3) SOP RAG with upload UI, (4) sensor pipeline detail — see `01_architecture_ingestion.md` |
| Governance | Constitution `CLAUDE.md`/`AGENTS.md` (I-1…I-12); decision log D1–D15; prior audits `docs/architecture_audit/`, `docs/fable_audit/` |
| Known blockers | none for audit; decoder/fusion phases will need llama.cpp-or-equivalent GGUF runtime (not yet installed) |

No production code modified in Phase 0.
