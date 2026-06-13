# Test Cases — Recipe A Pipeline

**Status:** Phase 1 (design). Concrete enumerated cases realizing the
[Test Strategy & Plan](test_strategy_and_plan.md). IDs are stable and referenced
from test code (`# UT-SENS-03`) for traceability.

**ID scheme:** `UT` unit · `IT` integration · `E2E` end-to-end. Module tags:
`CFG, SCH, IO, SENS, TEXT, VID, ASM, CLI, EVAL`.

**Legend:** Pre = pre-conditions/fixtures · Steps = actions · Expected = pass
criteria.

---

## 1. Config — `common/config.py`

| ID | Title | Pre | Steps | Expected |
|----|-------|-----|-------|----------|
| UT-CFG-01 | Load valid config | `mini_config.yaml` | `load_config(path)` | Returns `PipelineConfig`; nested models populated; defaults applied where omitted |
| UT-CFG-02 | Relative paths resolved | valid config w/ relative paths | load | All `paths.*` are absolute, rooted at repo root |
| UT-CFG-03 | Missing required key | config without `sensor` | load | `ConfigError` mentioning `sensor` |
| UT-CFG-04 | Bad type | `pre_event_s: "sixty"` | load | `ConfigError`/`ValidationError` naming `pre_event_s` |
| UT-CFG-05 | Out-of-range threshold | `fs_estimation.min_plausible_hz: -5` | load | Rejected with key in message |
| UT-CFG-06 | Unsupported version | `version: "99.0"` | load | `ConfigError` about version |

## 2. Schemas — `common/schemas.py`

| ID | Title | Pre | Steps | Expected |
|----|-------|-----|-------|----------|
| UT-SCH-01 | Valid SensorWindowRow | field dict | construct | Instance created; defaults for omitted optionals |
| UT-SCH-02 | Span ordering | `start_s=5,end_s=2` | construct `Span` | `ValidationError` ("end_s < start_s") |
| UT-SCH-03 | Bad enum | `regime_label="spin"` | construct `IncidentRow` | `ValidationError` |
| UT-SCH-04 | JSON-list round-trip | row w/ 2 spans + chunk-id lists | to-parquet → from-parquet → decode | Equal to original (spans, ids) |
| UT-SCH-05 | Required field missing | `IncidentRow` w/o `split` | construct | `ValidationError` naming `split` |

## 3. IO & IDs — `common/io_utils.py`, `common/ids.py`

| ID | Title | Pre | Steps | Expected |
|----|-------|-----|-------|----------|
| UT-IO-01 | Atomic write success | df, `tmp_path` | `write_parquet_atomic` | File exists; no `*.tmp` left; readable back equal |
| UT-IO-02 | Atomic write failure leaves original | existing file + patched failure mid-write | attempt write | Original unchanged; no partial/corrupt file |
| UT-IO-03 | JSON col round-trip (Span) | `list[Span]` | `dump_json_col`→`load_json_col` | Structurally equal |
| UT-IO-04 | JSON col round-trip (str ids) | `list[str]` | dump→load | Equal |
| UT-IO-05 | exists_and_fresh true | output newer than inputs | call | `True` |
| UT-IO-06 | exists_and_fresh stale | input touched after output | call | `False` |
| UT-ID-01 | Deterministic id | same args twice | `incident_id(...)` ×2 | Identical strings |
| UT-ID-02 | Distinct inputs distinct ids | different `t_event_s` | compute | Different ids |

## 4. Sensor ETL — `sensor_etl.py`

### Normalizer
| ID | Title | Pre | Steps | Expected |
|----|-------|-----|-------|----------|
| UT-SENS-01 | Column map rename | df cols `X,Y,Z`; map→`ax,ay,az` | `normalize` | Canonical order `time_s,ax,ay,az`; old names gone |
| UT-SENS-02 | Unmapped columns dropped | extra `junk` col | normalize | `junk` absent from output |
| UT-SENS-03 | Non-monotonic time repaired | `nonmonotonic_time.csv`, known fs | normalize | `time_s` strictly increasing; reconstructed from fs |

### FsEstimator
| ID | Title | Pre | Steps | Expected |
|----|-------|-----|-------|----------|
| UT-SENS-04 | median_dt recovers fs | signal sampled at 2000 Hz | `estimate(method=median_dt)` | ≈2000 Hz within 1% |
| UT-SENS-05 | Implausible fs rejected | dt implying 5 Hz, min=100 | estimate | Raises/flags; run skipped |
| UT-SENS-06 | Fixed fs honored | `fs_hz=1000` in cfg | estimate(method=fixed) | Returns 1000 exactly |

### EventDetector (RMS / z-score thresholding)
| ID | Title | Pre | Steps | Expected |
|----|-------|-----|-------|----------|
| UT-SENS-07 | Detect K bursts | `sine_with_bursts.csv`, K=3 at known t | `detect` | Exactly 3 events; `t_event_s` near injected times (±hop) |
| UT-SENS-08 | No false positives on noise | pure sub-threshold noise | detect | 0 events |
| UT-SENS-09 | Merge close events | 2 bursts < `min_separation` apart | detect | Merged into 1 event |
| UT-SENS-10 | Drop short blip | burst < `min_duration` | detect | Dropped (0 from it) |
| UT-SENS-11 | Threshold monotonicity | raise `threshold_value` | detect | Event count non-increasing |

### WindowCarver / EvidenceSpanExtractor
| ID | Title | Pre | Steps | Expected |
|----|-------|-----|-------|----------|
| UT-SENS-12 | Window length & zeroing | event mid-recording, pre=60/post=30, fs known | `carve` | `≈90 s` span; `n_samples≈90*fs`; `t_rel_s` min≈−60, ≈0 at event, max≈+30 |
| UT-SENS-13 | Drop partial window | event 5 s from start, drop=true | carve | Returns `None` |
| UT-SENS-14 | Keep partial when allowed | same, drop=false | carve | Returns truncated window |
| UT-SENS-15 | Evidence spans cover crossing | known burst interval | `extract` | Span(s) overlap burst, padded by `pad_s`, ≤`max_spans`, rel-time |

### SensorETL.run (integration)
| ID | Title | Pre | Steps | Expected |
|----|-------|-----|-------|----------|
| IT-SENS-01 | CSV → windows + index | tmp workspace, 1 csv w/ 3 bursts | `SensorETL.run()` | 3 window parquet files; 3 valid `SensorWindowRow`s in index; `t_rel_s` present |
| IT-SENS-02 | Dry run writes nothing | same | `run(dry_run=True)` | No files written; summary reports intended counts |
| IT-SENS-03 | Disabled dataset skipped | dataset `enabled:false` | run | 0 windows from it; logged skip |
| IT-SENS-04 | Idempotent re-run | run twice | run, run | Second run skips existing; identical ids |

## 5. Text ETL — `text_etl.py`

| ID | Title | Pre | Steps | Expected |
|----|-------|-----|-------|----------|
| UT-TEXT-01 | Chunk token bounds | `tiny_manual.md` | `chunk` | Every chunk `min_tokens ≤ n ≤ max_tokens` (except a lone final remainder) |
| UT-TEXT-02 | No cross-heading chunk | manual w/ 2 headings | chunk | No chunk text spans two headings |
| UT-TEXT-03 | Overlap honored | long section | chunk | Consecutive chunks share ≈`overlap_tokens` |
| UT-TEXT-04 | Giant paragraph hard-split | one paragraph > max | chunk | Split into ≤max pieces; none exceed max |
| UT-TEXT-05 | Token count fallback | tokenizer unavailable | `count_tokens` | Whitespace estimate returned; warning logged once |
| UT-TEXT-06 | Topic tagging hit | text w/ "chatter","tool wear" | `tag` | Tags include `vibration`,`tool_wear` |
| UT-TEXT-07 | No spurious tags | neutral text | tag | Empty/expected-only tags |
| UT-TEXT-08 | docx read or clean skip | `tiny_manual.docx` | `DocReader.read` | Text extracted; or skipped+logged if lib missing |
| IT-TEXT-01 | Manuals → chunks index | tmp workspace, 1 md + 1 docx | `TextETL.run()` | `text_chunks.parquet` valid; `doc_type` set; ids unique |

## 6. Video ETL — `video_etl.py`

| ID | Title | Pre | Steps | Expected |
|----|-------|-----|-------|----------|
| UT-VID-01 | Probe parse | mocked ffprobe JSON | `FfprobeReader.probe` | Correct fps/duration/codec/dims |
| UT-VID-02 | ffmpeg arg vector | normalize cfg 720p/30fps | build command | Args contain scale=720, fps=30, libx264, mp4 |
| UT-VID-03 | Skip conformant | clip already 720p/30fps | `normalize` | No ffmpeg call (copy/link); logged skip |
| UT-VID-04 | ffmpeg failure handled | mocked non-zero exit | normalize | `VideoToolError` w/ context |
| UT-VID-05 | ffmpeg missing handled | binary not found (mock) | normalize | `VideoToolError` w/ install hint |
| UT-VID-06 | Tag merge present | tags csv has clip | `TagMerger.merge` | Regime/condition/source from csv |
| UT-VID-07 | Tag merge absent | clip not in csv | merge | All `unknown` |
| E2E-VID-01 | Real normalize (skipif ffmpeg) | `clip_2s.mp4` | `VideoETL.run()` | Output 720p/30fps mp4; valid index row; probed duration≈2 s |

## 7. Incident Assembly — `assemble_incidents.py`

| ID | Title | Pre | Steps | Expected |
|----|-------|-----|-------|----------|
| UT-ASM-01 | Severity buckets | amplitudes spanning quantiles | `LabelDeriver.derive` | low/med/high assigned by quantile bin |
| UT-ASM-02 | Label defaults | empty meta | derive | All labels `unknown` |
| UT-ASM-03 | Video regime match | index w/ roughing+idle; incident=roughing | `VideoMatcher.match` | Picks a roughing clip; `alignment_method=label_match` |
| UT-ASM-04 | Idle fallback | no regime match, fallback on | match | Picks idle clip; `alignment_method=idle_fallback` |
| UT-ASM-05 | No match, no fallback | none + fallback off | match | `(None, none)`; incident flagged missing video |
| UT-ASM-06 | Seeded pick reproducible | same seed twice | match ×2 | Same clip chosen |
| UT-ASM-07 | Text retrieve count | chunks w/ topics; k=[1,3] | `TextRetriever.retrieve` | 1–3 ids, correct `doc_type` |
| UT-ASM-08 | failure→topics mapping | failure=`chatter` | retrieve | Chunks tagged vibration/spindle/feed preferred |
| UT-ASM-09 | Topic relax on miss | no exact topic match | retrieve | Falls back to broader topics; ≥min or flagged |
| UT-ASM-10 | Split fractions | 100 incidents, default fractions | `SplitAssigner.assign` | Counts within ±1 of 70/15/10/5 |
| UT-ASM-11 | No group leakage | rows sharing `source_dataset` | assign | All same-group rows in one split |
| UT-ASM-12 | Split reproducible | same seed twice | assign ×2 | Identical assignment |
| IT-ASM-01 | Assemble from fixtures | synthetic sensor/video/text indices | `IncidentAssembler.run()` | ≥1 valid `IncidentRow`; JSON fields parse |
| IT-ASM-02 | Referential integrity | output incidents | check ids | Every `sop/maintenance_chunk_id`∈ text_chunks; `video_file`∈ video_index |
| IT-ASM-03 | Missing upstream fail-fast | no `sensor_windows.parquet` | run | Fails fast naming `sensor` command |
| IT-ASM-04 | Incident w/o video flagged | video index empty, fallback off | run | Row has null video + counted in summary |

## 8. CLI & Evaluation — `cli.py`, `evaluate.py`

| ID | Title | Pre | Steps | Expected |
|----|-------|-----|-------|----------|
| UT-CLI-01 | Subcommand wiring | mini config | `cli sensor --dry-run` | Loads config, runs stage dry, prints summary, exit 0 |
| UT-CLI-02 | Missing upstream exit | run `assemble` first | invoke | Non-zero exit; message names prerequisite |
| UT-CLI-03 | `--limit` honored | many inputs, `--limit 1` | invoke | Processes 1 item |
| IT-EVAL-01 | Metrics on fixture | known `incidents.parquet` | `evaluate` | Reported incident-hours, distributions, %-with-chunks match expected |
| IT-EVAL-02 | Malformed-JSON detection | inject 1 bad JSON cell | evaluate | Flagged in malformed count |

## 9. End-to-end — full pipeline

| ID | Title | Pre | Steps | Expected |
|----|-------|-----|-------|----------|
| E2E-01 | Demo build (skipif ffmpeg) | micro-fixtures for all 3 modalities + `mini_config.yaml` | `cli all` | `incidents.parquet` produced; ≥1 fully-linked row; no dangling refs; JSON parses; split present |
| E2E-02 | Determinism re-run | run E2E-01 twice (same seed) | compare outputs | Identical incident ids, video picks, splits |
| E2E-03 | Evaluation gate | demo `incidents.parquet` | `cli evaluate` | Report renders; sanity metrics computed; no crash on small N |

---

## 10. Coverage matrix (requirement → cases)

| Requirement (from design) | Cases |
|---------------------------|-------|
| Time normalization correct | UT-SENS-01..03, UT-SENS-12 |
| RMS / z-score thresholding | UT-SENS-07..11 |
| Sampling-rate estimation | UT-SENS-04..06 |
| Incident windowing + `t_rel_s` | UT-SENS-12..14, IT-SENS-01 |
| Evidence spans | UT-SENS-15 |
| Chunking ~150–200 tokens, heading-aware | UT-TEXT-01..04 |
| Topic tagging | UT-TEXT-06,07 |
| Video normalize 720p/30fps | UT-VID-02,03, E2E-VID-01 |
| Cross-modal video match | UT-ASM-03..06 |
| Text retrieval 1–3 chunks/type | UT-ASM-07..09 |
| Splits, no leakage, reproducible | UT-ASM-10..12 |
| Schema integrity / round-trip | UT-SCH-*, UT-IO-03,04 |
| Referential integrity | IT-ASM-02 |
| Idempotency / determinism | UT-IO-05,06, IT-SENS-04, E2E-02 |
| End-to-end build | E2E-01, IT-ASM-01 |
| Evaluation metrics | IT-EVAL-01,02, E2E-03 |
