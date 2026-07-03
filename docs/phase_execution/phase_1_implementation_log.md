# Phase 1 — Implementation Log (2026-07-03)

Base commit: `9c9733f`. All changes additive except two small edits
(README quickstart pointer, .gitignore entries, runbook expectation fix).

## Files created

| File | Purpose | ~Lines |
|---|---|---|
| `scripts/generate_sample_data.py` | Seeded synthetic raw-data generator (sensor CSVs, manuals, tags CSV, optional ffmpeg clips) | 185 |
| `config/dataset.sample.yaml` | Standalone smoke config → `*_sample` dirs | 140 |
| `tests/unit/test_sample_data.py` | 4 unit tests for the generator | 50 |
| `docs/runbook.md` | Fresh-clone + real-corpus + tests + GPU runbook | 95 |
| `.env.example` | No-secrets placeholder + future model-phase vars | 16 |
| `docs/phase_execution/phase_1_*.md` | This phase's ETVX record set | — |

## Files edited

| File | Change |
|---|---|
| `docs/_sdd/decisions.md` | Appended D10 (window convention operationalization, user-approved) and D11 (GPU-first policy + probed hardware envelope) |
| `.gitignore` | Ignore `data_pipeline/data_raw_sample/`, `data_pipeline/data_processed_sample/` |
| `README.md` | Added 4-line sample-data quickstart pointing at the runbook |
| `docs/runbook.md` | Post-run fix: expectation updated to the observed `written=5` (one good run also crosses the zscore threshold) |

## Application code modified

**None.** `src/`, `contracts/`, `streamlit_app.py` untouched (verified via
`git status` — only the files above changed).

## Issues hit and fixed during implementation

1. Generator type annotation bug (`rng: np.ndarray` → `np.random.Generator`) —
   caught on self-review before running, fixed.
2. Runbook expectation stated "good runs yield none"; the actual run produced
   5 incidents from 8 runs (one good run crossed zscore 4.0). Documented the
   observed behavior instead of tuning the threshold — the smoke path's job is
   to exercise the pipeline, not to be a detector benchmark.

## GPU baseline established (decision D11)

- `nvidia-smi`: RTX 3060, 12 GB, driver 595.79, CUDA 13.2.
- `torch 2.6.0+cu124`, `torch.cuda.is_available() == True`.
- Reported limitation: Qwen2.5-VL-7B fp16 (~15–16 GB) exceeds 12 GB → Phase 7
  needs int4/AWQ quantization or the 3B variant (user decision at Phase 7 gate).
- Cosmetic: torch emits a `pynvml` deprecation FutureWarning on import
  (harmless; noted for when torch becomes a declared dependency in Phase 4).
