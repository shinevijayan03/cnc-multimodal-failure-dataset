# Phase 1 — User Review Request

```text
PHASE 1 COMPLETE — USER REVIEW REQUIRED

What changed:
- Fresh-clone bootstrap: scripts/generate_sample_data.py + config/dataset.sample.yaml
  (seeded synthetic corpus; isolated *_sample dirs; never touches real data).
- docs/runbook.md (sample path, real path, tests, GPU environment).
- .env.example; .gitignore entries for sample dirs; README quickstart pointer.
- Decisions D10 (window convention) and D11 (GPU-first policy) recorded in
  docs/_sdd/decisions.md with the probed hardware envelope.
- 4 new unit tests. No application code (src/, contracts/) was modified.

How to test:
Run the three-command fresh-clone path and confirm the pipeline completes and
the explorer starts.

Commands:
  python scripts/generate_sample_data.py
  python -m src.cli all --config config/dataset.sample.yaml
  streamlit run streamlit_app.py
  pytest -q

Expected result:
  - generator prints a JSON summary (8 sensor CSVs, 2 manuals, 2 clips)
  - pipeline prints: [sensor] written=5 · [text] written=13 · [video] written=2
    · [assemble] written=5, exit code 0
  - Streamlit starts; pytest reports 110 passed, 1 skipped

Known limitations:
  - `evaluate` on the sample config FAILs scale tiers by design (tiny corpus).
  - GPU finding to acknowledge: Qwen2.5-VL-7B fp16 (~15-16 GB) does not fit the
    RTX 3060 12 GB → Phase 7 will need an int4/AWQ-quantized 7B or the 3B
    variant. Decision scheduled at the Phase 7 entry gate.
  - Streamlit sidebar must be pointed at data_pipeline/data_processed_sample to
    browse the sample build (default remains the real processed dir).

Please test and provide feedback.
I will incorporate your feedback before moving to Phase 2.
```
