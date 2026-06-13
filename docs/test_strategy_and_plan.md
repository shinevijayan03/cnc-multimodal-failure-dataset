# Test Strategy & Plan — Recipe A Pipeline

**Status:** Phase 1 (design). **Companion:** [Test Cases](test_cases.md) (concrete
enumerated cases) · [Software Design](software_design.md) (testing seams §12).

This document has two parts: a **Test Strategy** (high-level: objectives, scope,
types, environment, tooling) and a **Test Plan** (concrete: what to test per
module, fixtures, and when tests run).

---

# Part A — Test Strategy

## A.1 Objectives

1. **Correctness of the numeric core** — sampling-rate estimation, RMS/z-score
   event detection, window carving, `t_rel_s` zeroing, chunk token-bounding,
   split fractions. These are the parts whose bugs silently corrupt the dataset.
2. **Schema integrity at boundaries** — every written row conforms to its
   Pydantic model; JSON-list fields round-trip; no dangling cross-modal ids.
3. **Robustness** — malformed/edge inputs are skipped-and-logged, not crashed-on
   (unless `fail_fast`).
4. **Idempotency & determinism** — re-running with the same inputs+seed yields
   identical outputs (ids, splits, picks).
5. **End-to-end integrity** — a tiny demo subset produces a valid
   `incidents.parquet` with linked modalities.

## A.2 Scope

**In scope:** all `src/` units — `common/` (config, schemas, io, ids),
`sensor_etl`, `text_etl`, `video_etl`, `assemble_incidents`, `cli`, `evaluate`.

**Out of scope (this project):** correctness of third-party libs (pandas,
pyarrow, ffmpeg); the *scientific* validity of heuristics (that is judged by
[Evaluation Criteria](evaluation_criteria.md), not unit tests); downstream model
training; GUI/perf/load testing.

## A.3 Test types & the pyramid

```
        ▲  few   End-to-end / smoke   (CLI `all` on micro-fixtures, real ffmpeg ×1)
       ╱ ╲
      ╱   ╲  some Integration         (per-stage run() on tmp dirs, indices join)
     ╱_____╲ many Unit                (pure numeric + schema + io, mocked subprocess)
```

- **Unit** — pure functions & small classes; no real IO except `tmp_path`;
  `ffmpeg`/`tiktoken` mocked. Fast (<1 s each), the bulk of the suite.
- **Integration** — one stage's `run()` end-to-end over a temp workspace; assert
  on the produced index + `RunSummary` counts; assert cross-index referential
  integrity in `assemble`.
- **End-to-end / smoke** — `cli all` on micro-fixtures (incl. one real `ffmpeg`
  normalize) → valid `incidents.parquet`; one determinism re-run check.

## A.4 Environment & tooling

- **Runner:** `pytest`; **coverage:** `pytest-cov`; **property tests:**
  `hypothesis` (optional, for numeric invariants); **fixtures:** `tmp_path`,
  shared factories in `tests/conftest.py`.
- **Static gates:** `ruff` (lint), `mypy` (types on `common/` + signatures),
  `black`/`ruff format` (style) — advisory in CI, not test failures.
- **ffmpeg:** required for exactly one e2e test; that test is `skipif` ffmpeg is
  absent so the unit suite runs anywhere.
- **Determinism:** every test that touches randomness passes an explicit seed.

## A.5 Coverage targets (advisory, not gating a thesis)

| Area | Target |
|------|--------|
| Numeric core (detect/carve/fs/chunk/split) | ≥ 90 % line + key branch |
| `common/` (config, schemas, io, ids) | ≥ 85 % |
| ETL orchestration `run()` glue | exercised by ≥1 integration test each |
| Overall | ≥ 80 % |

## A.6 Entry / exit criteria

- **Entry:** Stage 0 scaffolding merged; fixtures generated; config loads.
- **Exit (per stage):** unit cases for its numeric core pass; one integration
  test green; no schema-validation failures on fixtures.
- **Exit (M1 milestone):** full e2e smoke green; determinism re-run identical;
  evaluation report runs on demo output.

## A.7 Risks to test quality & mitigations

| Risk | Mitigation |
|------|-----------|
| Real datasets unavailable during dev | synthetic fixtures with *known* injected events; one optional test reads a real sample if present |
| ffmpeg env variance (Windows) | mock in unit; single `skipif` e2e |
| Heuristic "correctness" is fuzzy | test *invariants/properties* (counts, monotonicity, bounds), not exact magic values |
| Flaky randomness | single seeded `rng`; assert determinism explicitly |

---

# Part B — Test Plan (concrete)

## B.1 What to test per module

### `common/config.py`
- Loads valid YAML → `PipelineConfig`; relative paths resolved to absolute.
- Missing required key / bad type / out-of-range threshold → `ConfigError`
  naming the key.
- Unsupported `version` → rejected.

### `common/schemas.py`
- Valid rows construct; `Span` rejects `end_s < start_s`.
- Bad enum value (e.g. `regime="spin"`) → `ValidationError`.
- JSON-list fields serialize→Parquet→deserialize unchanged (round-trip).

### `common/io_utils.py` / `ids.py`
- `write_parquet_atomic` leaves no temp file on success; original intact on
  simulated failure mid-write.
- `dump/load_json_col` round-trip for `list[Span]` and `list[str]`.
- `exists_and_fresh` true only when output newer than all inputs.
- ids are deterministic (same input→same id) and collision-resistant across
  distinct inputs.

### `sensor_etl.py`
- **`Normalizer`:** `column_map` rename → canonical order; non-monotonic time
  repaired from `fs_hz`; unmapped columns dropped.
- **`FsEstimator`:** `median_dt` recovers known fs of a synthetic signal within
  tolerance; implausible fs rejected; `fixed`/`metadata` honored.
- **`EventDetector`:** signal with N injected bursts → N events; sub-threshold
  noise → 0 events; bursts within `min_separation` → merged; blip <
  `min_duration` → dropped.
- **`WindowCarver`:** window length == pre+post; `t_rel_s` zero at event; partial
  window dropped when configured, kept otherwise.
- **`EvidenceSpanExtractor`:** spans cover the crossing, padded, capped at
  `max_spans`, in incident-relative time.
- **`SensorETL.run`** (integration): synthetic CSV → expected #windows, files
  written, valid index rows; `dry_run` writes nothing.

### `text_etl.py`
- **`DocReader`:** md/txt parsed; headings preserved as boundaries; docx read (or
  skipped cleanly if lib absent).
- **`Chunker`:** every chunk within `[min,max]` tokens; no chunk crosses a
  heading; overlap honored; heading-less giant paragraph hard-split.
- **`count_tokens`:** tiktoken path and whitespace fallback both return sane
  counts; fallback used when tokenizer missing.
- **`TopicTagger`:** text with known keywords → expected topic tags; clean text →
  no spurious tags.
- **`TextETL.run`** (integration): fixture manual → chunks in index, all valid.

### `video_etl.py`
- **`FfprobeReader`:** parses mocked ffprobe JSON → fps/duration/codec.
- **`FfmpegNormalizer`:** builds correct ffmpeg arg vector (720p/30fps/H.264);
  skips already-conformant; raises `VideoToolError` on non-zero exit / missing
  binary (mocked).
- **`TagMerger`:** present tags merged; absent → `unknown`.
- **`VideoETL.run`** (integration, real ffmpeg, `skipif`): 2 s fixture mp4 →
  normalized 720p/30fps clip + valid index row.

### `assemble_incidents.py`
- **`LabelDeriver`:** severity buckets from amplitude quantiles; defaults
  `unknown` when meta absent.
- **`VideoMatcher`:** picks regime-matching clip; idle fallback when none;
  `alignment_method` set correctly; seeded pick reproducible.
- **`TextRetriever`:** returns within `[min,max]` chunks of the right `doc_type`;
  failure→topics mapping respected; relaxes topics when none match.
- **`SplitAssigner`:** fractions within tolerance; same `group_key` never spans
  two splits; seeded → reproducible.
- **`IncidentAssembler.run`** (integration): tiny 3-modality fixtures → valid
  `IncidentRow`s; **referential integrity** (every `sop/maintenance_chunk_id`
  exists in `text_chunks`; `video_file` exists in `video_index`); missing
  upstream index → fail-fast error.

### `cli.py` / `evaluate.py`
- Each subcommand wires config→stage→summary; `--dry-run`, `--limit` honored;
  missing-upstream → actionable non-zero exit.
- `evaluate` computes the [Evaluation Criteria](evaluation_criteria.md) metrics on
  a known fixture and matches expected values.

## B.2 Test data & fixtures strategy

All fixtures are **tiny, synthetic, and generated/committed under
`tests/fixtures/`** — no licensed data in the repo.

| Fixture | How produced | Used by |
|---------|--------------|---------|
| `sine_with_bursts.csv` | numpy: baseline noise + K Gaussian bursts at known times, known fs | sensor unit + integration |
| `nonmonotonic_time.csv` | timestamps with gaps/dupes | normalizer/fs tests |
| `tiny_manual.md` | 2–3 headings, paragraphs w/ seeded keywords | text unit + integration |
| `tiny_manual.docx` | generated via python-docx in a fixture builder | docx reader test |
| `clip_2s.mp4` | generated once via ffmpeg `testsrc` (or committed tiny clip) | video e2e |
| `video_tags.csv` | hand-written regime/condition for fixture clips | tag merge / assemble |
| `mini_config.yaml` | points all paths at `tmp_path` | every integration test |
| factory builders | `make_sensor_index()`, `make_video_index()`, `make_chunks()` in `conftest.py` | assemble tests (no need to run upstream) |

Principle: unit tests use **in-memory** arrays/builders; integration tests use a
**temp workspace** seeded from these fixtures; the assembler can be tested from
synthetic indices without running Stages 1–3.

## B.3 When tests run (cadence)

- **During development (per module):** run that module's unit tests on save;
  numeric core kept green continuously.
- **Per stage complete:** that stage's integration test must pass before moving on
  (gates the milestone in [Implementation Plan](implementation_plan.md)).
- **Full-pipeline smoke:** the `cli all` e2e + determinism re-run, executed before
  each milestone sign-off (M1, M2) and before any thesis-build run.
- **CI (if configured):** unit + integration on every push; e2e (real ffmpeg) on
  a runner that has ffmpeg, else `skipif`.
- **Pre-thesis-build:** full suite + evaluation report must be green.

## B.4 Traceability

Every concrete case in [Test Cases](test_cases.md) carries an ID (`UT-*`, `IT-*`,
`E2E-*`) mapped back to the module/requirement here, so coverage of each
requirement is auditable in review.
