# Phase 1 — Design

## Approach

Smallest safe change (I-11): no application module is modified. The bootstrap
is additive — a generator script plus a second config file that points at
`*_sample` directories, so the real `data_pipeline/data_raw` and
`data_pipeline/data_processed` trees can never be touched by the smoke path.

## Components

| Piece | Design choice | Why |
|---|---|---|
| `scripts/generate_sample_data.py` | Synthesizes Bosch-style x/y/z CSVs (2 kHz, 20 s, DC offset ≈ -1015, one Gaussian burst on z for "bad" runs), two markdown manuals rich in the configured topic keywords, `video_tags.csv`, and two 6 s ffmpeg `lavfi` clips when ffmpeg exists (`--no-video` to skip) | Mirrors `tests/conftest.make_bursts_df` semantics so the existing readers/detectors work unchanged; seeded `np.random.default_rng` for determinism |
| `config/dataset.sample.yaml` | Full standalone config; paths → `data_raw_sample` / `data_processed_sample`; zscore detector (bursts are transients, unlike the quantile setting for the continuous real corpus); `whitespace` tokenizer (no optional deps); `max_windows_per_run: 1` | Standalone file keeps `load_config` untouched; explicit comments explain each divergence from `config/dataset.yaml` |
| `.gitignore` additions | `data_pipeline/data_raw_sample/`, `data_pipeline/data_processed_sample/` | Generated data is recreatable; never committed |
| `tests/unit/test_sample_data.py` | 4 tests: tree layout, reader-contract columns/row-count/DC offset, burst presence (bad std > 2× good std), byte-identical determinism across same-seed runs | Cheap (`--no-video`), no ffmpeg dependency in CI |
| `docs/runbook.md` | Fresh-clone path, real-corpus path, test commands, GPU section with re-probe commands | Single place a user gate can point to |
| `.env.example` | Documents zero current secrets + future HF_HOME/TORCH_HOME/CUDA_VISIBLE_DEVICES | Security-hygiene rubric line |
| `docs/_sdd/decisions.md` D10/D11 | Window-convention operationalization; GPU-first policy with probed hardware envelope and the Qwen2.5-VL-7B-fp16-doesn't-fit finding | Constitution requires decisions in the log; user directive recorded verbatim |

## Alternatives rejected

- *Reusing `tests/conftest.py` factories from the script* — scripts must not
  import test code; duplicating ~15 lines of burst synthesis is cheaper than
  moving factories into `src/` for this scope.
- *One config with CLI overrides* — `load_config` has no override mechanism;
  adding one touches application code, out of Phase 1 scope.
- *Committing pre-built sample parquet artifacts* — violates the repo's
  data-not-committed convention; generation is fast (<5 s).
