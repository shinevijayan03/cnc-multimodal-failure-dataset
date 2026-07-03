# 00 — Audit Execution Log

Audit date: 2026-07-03. No application code was modified during this audit.
Only documentation artifacts under `docs/architecture_audit/`, `docs/build_plan/`,
`docs/phase_execution/`, and `docs/validation/` were created.

## Phase A0 — Repository baseline

| Command | Output |
|---|---|
| `git status --porcelain` | (empty — working tree clean) |
| `git branch --show-current` | `codex/complete-pending-phases` |
| `git rev-parse HEAD` | `547f2c12e82d08c0e45a0e188ab1ade010179e01` |
| `find . -maxdepth 3 -type f ...` | 160+ files inventoried; see `01_codebase_inventory.md` |

Pre-existing generated doc sets found (from prior loops, committed at HEAD):
`docs/codebase_audit/`, `docs/context/`, `docs/build_iterations/`,
`docs/refactor_ecosystem/`, `docs/_sdd/`, `docs/_eval/`, `docs/_data/`.
This audit re-verified all claims directly against code and runtime; it does not
inherit unverified statements from those documents.

## Phase A2 — Runtime execution (all executed 2026-07-03 on Windows 11, Python 3.12.7)

| # | Command | Result |
|---|---|---|
| 1 | `python --version` | `Python 3.12.7` (Anaconda) |
| 2 | `python -c "import pandas, pydantic, streamlit, typer"` | `deps ok` — dependencies already installed |
| 3 | `python -m pytest -q` | **106 passed, 1 skipped in 8.17s** |
| 4 | `python -m src.cli evaluate --config config/dataset.yaml --tier mvp` | **GRADE: PASS** — n_incidents=1702, split {train:1192, val:255, test:170, human_eval:85}, pct_fully_multimodal=1.0 |
| 5 | `python -m src.eval.run --fixtures oracle --no-write` | Runs; all fixture metrics printed (schema_valid_rate 1.0, attr_precision 1.0, unsupported_claim_rate 0.0, iou 1.0) |
| 6 | Streamlit smoke: `python -m streamlit run streamlit_app.py --server.headless true --server.port 8599` then `GET /healthz` | **healthz_ok=True** (HTTP 200); "You can now view your Streamlit app" banner printed; process stopped cleanly |
| 7 | `python -m src.cli sensor --dry-run --limit 2` | `[sensor] [DRY-RUN] processed=2 written=2 skipped=1 errors=0` |
| 8 | `python -m src.cli text --dry-run --limit 1` | `[text] [DRY-RUN] discovered=5 processed=1 written=1 errors=0` |
| 9 | `Get-Command ffmpeg` | ffmpeg 8.1.1 present on PATH (WinGet install) |
| 10 | `ruff check src tests contracts scripts` | `All checks passed!` |
| 11 | `python -m compileall -q src contracts scripts streamlit_app.py` | OK |

The one skipped test is the browser-level UI smoke test
(`tests/ui/test_streamlit_browser_smoke.py`), opt-in via `RUN_BROWSER_SMOKE=1`
per `pyproject.toml` marker config.

Note: `python scripts/build_dataset.py` was **not** re-executed during the audit
because it rewrites tracked artifacts (`docs/_data/*`, `data/splits/*`); its
behavior is verified instead by `tests/unit/test_tgfx_dataset.py` (part of the
green pytest run) and by the existing committed outputs.

## Constitution constraints observed during audit

Per `CLAUDE.md` (TGFX Constitution): `data/splits/test.jsonl` was **not read,
printed, grepped, or summarized** (I-4). No numbers in these documents are
fabricated (I-7) — every metric traces to a command in the table above.

## Runtime classification

```text
RUNS
```

See `08_runtime_execution_report.md` for detail.
