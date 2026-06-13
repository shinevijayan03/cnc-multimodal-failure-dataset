# Evaluation & Dataset-Quality Criteria — Recipe A

**Status:** Phase 1 (design). Defines *how we judge whether the dataset Recipe A
produces is good enough*, with quantitative metrics, thresholds for two tiers
(thesis-MVP vs extended benchmark), and how each metric is computed.

**Companion:** [Evaluation Criteria are checked by] `src/evaluate.py` /
`notebooks/evaluate_dataset.ipynb` (Stage 7 of the
[Implementation Plan](implementation_plan.md)).

> Distinction from testing: [Test Cases](test_cases.md) verify the *code is
> correct*; this document verifies the *dataset is fit for purpose*. Code can be
> bug-free yet produce a thin/imbalanced dataset — these metrics catch that.

---

## 1. Metric families

Five families, each a section below:
1. **Scale & coverage** — is there enough data, across the right axes?
2. **Cross-modal completeness** — are incidents actually multimodal?
3. **Distribution & balance** — is any class/regime pathologically dominant?
4. **Integrity & sanity** — are references valid, files present, JSON well-formed?
5. **Grounding quality** — do evidence spans / links look plausible?

Each metric has: definition, how computed, MVP threshold, Extended threshold.

---

## 2. Scale & coverage

| Metric | Definition | Computation |
|--------|-----------|-------------|
| `total_incident_hours` | Σ window durations / 3600 | sum(`window_end_s−window_start_s`) over `incidents.parquet` |
| `n_incidents` | row count | `len(incidents)` |
| `n_video_clips` | distinct normalized clips | `video_index` rows |
| `text_pages_equiv` | chunks × tokens / 500 (≈page) | Σ`n_tokens`/500 over `text_chunks` |
| `n_sensor_datasets_used` | distinct `source_dataset` | nunique |

| Metric | **MVP (thesis)** | **Extended (benchmark)** |
|--------|------------------|--------------------------|
| `total_incident_hours` | ≥ 2 h (demo proof) | **≥ 72 h** |
| `n_video_clips` | ≥ 20 | **≈ 1,000** |
| `text_pages_equiv` | ≥ 30 | **≥ 300–400** |
| `n_sensor_datasets_used` | ≥ 1 | ≥ 3 |

## 3. Cross-modal completeness

| Metric | Definition | Computation |
|--------|-----------|-------------|
| `pct_with_video` | % incidents with non-null `video_file` | mean(`video_file` notnull) |
| `pct_with_sop` | % with ≥1 SOP chunk | mean(len(`sop_chunk_ids`)≥1) |
| `pct_with_maint` | % with ≥1 maintenance chunk | mean(len(`maintenance_chunk_ids`)≥1) |
| `pct_with_sop_and_maint` | % with ≥1 of **each** | mean(both≥1) |
| `pct_fully_multimodal` | % with video AND sop AND maint | mean(all three) |
| `mean_sop_chunks`, `mean_maint_chunks` | avg chunks/incident | mean(len(...)) |

| Metric | **MVP** | **Extended** |
|--------|---------|--------------|
| `pct_with_sop_and_maint` | ≥ 80 % | **≥ 95 %** |
| `pct_with_video` | ≥ 70 % | ≥ 90 % |
| `pct_fully_multimodal` | ≥ 60 % | ≥ 85 % |
| `mean_sop_chunks` / `mean_maint_chunks` | within [1,3] | within [1,3] |

## 4. Distribution & balance

| Metric | Definition | Computation |
|--------|-----------|-------------|
| `failure_family_dist` | count + % per family | `value_counts(failure_family)` |
| `regime_dist` | per regime | `value_counts(regime_label)` |
| `severity_dist` | per severity bin | `value_counts(severity_label)` |
| `split_dist` | per split + leakage check | `value_counts(split)` + group check |
| `dominant_class_share` | max class % (failure family) | max of family % |
| `pct_unknown_failure` | % `failure_family==unknown` | mean(==unknown) |
| `entropy_failure` | normalized Shannon entropy of family dist | H/Hmax |

| Metric | **MVP** | **Extended** |
|--------|---------|--------------|
| `dominant_class_share` | ≤ 80 % | **≤ 50 %** |
| `pct_unknown_failure` | ≤ 70 % | **≤ 30 %** |
| `entropy_failure` | ≥ 0.3 | ≥ 0.6 |
| `split_dist` | ≈ configured fractions ±2 % | ±1 %; **zero** group leakage |
| each non-unknown family | ≥ 1 incident | ≥ 30 incidents (statistical floor) |

## 5. Integrity & sanity

| Metric | Definition | Computation | Threshold (both tiers) |
|--------|-----------|-------------|------------------------|
| `pct_missing_sensor_file` | sensor parquet path absent on disk | `~Path.exists()` | **0 %** |
| `pct_missing_video_file` | video path absent (when non-null) | exists check | **0 %** |
| `pct_dangling_chunk_id` | chunk id not in `text_chunks` | set-diff | **0 %** |
| `pct_malformed_json` | JSON-list field fails to parse | try `load_json_col` | **0 %** |
| `pct_bad_span` | span with `end_s<start_s` or out of window | validate vs window | **0 %** |
| `pct_duplicate_incident_id` | duplicated ids | `duplicated()` | **0 %** |
| `pct_window_len_mismatch` | \|dur − (pre+post)\| > tol | compare to config | ≤ 1 % (edge windows) |
| `fs_hz_plausible` | all fs in `[min,max]_plausible_hz` | range check | **100 %** |

Integrity metrics are **hard gates**: any non-zero on the 0 %-target rows fails
the build regardless of other scores.

## 6. Grounding quality (heuristic-aware)

These judge whether the *temporal grounding & evidence linking* look sensible.
They are softer (heuristics, not ground truth) and reported with caveats.

| Metric | Definition | Computation |
|--------|-----------|-------------|
| `pct_with_sensor_span` | % incidents with ≥1 sensor evidence span | mean(len≥1) |
| `mean_sensor_span_count` | avg spans/incident | mean(len) |
| `mean_sensor_span_frac` | avg fraction of window covered by spans | Σspan_dur/window_dur |
| `pct_event_near_zero` | % where an evidence span overlaps `t_rel_s≈0` | overlap check |
| `pct_label_match_alignment` | % video links via true `label_match` (not idle fallback) | mean(alignment==label_match) |
| `topic_link_relevance` (sampled) | manual/keyword check that retrieved chunks mention the failure topic | sampled audit (k=30) |

| Metric | **MVP** | **Extended** |
|--------|---------|--------------|
| `pct_with_sensor_span` | ≥ 90 % | ≥ 98 % |
| `mean_sensor_span_frac` | within (0, 0.6] (not whole window) | (0, 0.4] |
| `pct_event_near_zero` | ≥ 90 % | ≥ 98 % |
| `pct_label_match_alignment` | ≥ 50 % | ≥ 75 % |
| `topic_link_relevance` | ≥ 70 % of sampled | ≥ 85 % |

## 7. Success definition (roll-up)

A build is graded **PASS / WARN / FAIL**:

- **FAIL** if *any* §5 hard-gate is violated, OR `total_incident_hours` is below
  the active tier's floor, OR `pct_with_sop_and_maint` below tier floor.
- **WARN** if all hard gates pass but ≥1 soft metric (balance/grounding) misses
  its tier threshold — usable, but flagged for iteration.
- **PASS** if all metrics meet the active tier's thresholds.

**Active tier** is chosen by a CLI flag (`--tier mvp|extended`); thesis sign-off
targets `extended`, demo/M1 targets `mvp`.

---

## 8. How metrics are computed & reported

- **Where:** `src/evaluate.py` exposes `compute_metrics(incidents, sensor_idx,
  video_idx, text_chunks, cfg, tier) -> MetricsReport`; the notebook calls it and
  renders tables + a few plots (distributions, span-fraction histogram).
- **CLI:** `python -m src.cli evaluate --config config/dataset.yaml --tier extended`
  prints the metric table + PASS/WARN/FAIL and writes `data_processed/eval_report.{json,md}`.
- **Determinism:** metrics are pure functions of the indices; same inputs → same
  report (sampled audits use the global seed).
- **Artifacts:** machine-readable `eval_report.json` (for tracking across builds)
  + human-readable `eval_report.md`; plots saved under `data_processed/eval_plots/`.

## 9. Iteration loop (Phase 3)

```
build → evaluate(--tier) → PASS? ──► done
                         │ WARN/FAIL
                         ▼
        diagnose worst metric → adjust knobs in dataset.yaml
        (detection threshold, window len, topic map, more raw data) → rebuild
```

Typical levers per failing metric:
- low `total_incident_hours` → add raw datasets / lower detection threshold /
  longer windows.
- high `pct_unknown_failure` → enable `manual_labels` mode / improve
  `failure_to_topics` / label more runs.
- low `pct_with_sop_and_maint` → author more manuals / broaden `topic_keywords`.
- low `pct_label_match_alignment` → tag more video regimes / capture targeted clips.
- whole-window `mean_sensor_span_frac` → tighten `evidence_spans` padding/method.

## 10. Open evaluation questions

1. Confirm the **page-equivalent** definition (500 tokens/page assumed).
2. Confirm the **extended** family-balance floor (≥30/family) is realistic given
   label availability.
3. Should `topic_link_relevance` use a small **LLM-as-judge** rather than manual
   sampling at scale? (Defer to Phase 3.)
4. Do we need a **gold human-aligned subset** metric (true video↔sensor overlap)
   for `human_eval`? Ties to Overview open-question §8.7.
