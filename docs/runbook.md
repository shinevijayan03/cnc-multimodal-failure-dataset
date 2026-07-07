# Runbook — running the pipeline on any machine

Verified on Windows 11 / Python 3.12.7; the pipeline is pure Python except for
optional ffmpeg (video) and the GPU stack (model phases, from Build Phase 4).

## A. Fresh clone (no staged data) — sample smoke path

```bash
git clone https://github.com/shinevijayan03/cnc-multimodal-failure-dataset.git
cd cnc-multimodal-failure-dataset
python -m pip install -r requirements.txt

# 1. Synthesize tiny raw data (seeded, deterministic; ~12 MB, gitignored)
python scripts/generate_sample_data.py            # add --no-video without ffmpeg

# 2. Run the four ETL stages over it
python -m src.cli all --config config/dataset.sample.yaml

# 3. Browse the result
streamlit run streamlit_app.py                    # then point the sidebar at
                                                  # data_pipeline/data_processed_sample
```

Expected (verified 2026-07-03): stage summaries report
`[sensor] processed=8 written=5`, `[text] written=13`, `[video] written=2`,
`[assemble] written=5` — each "bad" run yields one burst incident and
occasionally a "good" run crosses the zscore threshold too. The output is
deterministic for a fixed seed. `python -m src.cli evaluate` against the
sample config will FAIL on scale metrics by design — tier thresholds target
the real corpus, not the smoke set.

## B. Real staged corpus

Stage raw data manually (never auto-downloaded — licensing):

```text
data_pipeline/data_raw/sensor_dataset/M*/OP*/{good,bad}/*.csv   # 2 kHz x/y/z
data_pipeline/data_raw/video_raw/*.mp4 + video_tags.csv
data_pipeline/data_raw/text_manuals/*.{md,txt,docx,pdf}
```

Then:

```bash
python -m src.cli all --config config/dataset.yaml
python -m src.cli evaluate --tier mvp            # expect GRADE: PASS
python scripts/build_dataset.py                  # TGFX manifest/ledger/splits
streamlit run streamlit_app.py
```

## C. Tests and checks

```bash
pytest -q                                        # full suite
pytest -q --cov=src --cov=contracts --cov=scripts --cov-report=term-missing
ruff check src tests contracts scripts
python -m src.eval.run --fixtures oracle --no-write   # TGFX metric harness
```

## D. GPU environment (decision D11 — local GPU always)

Probed 2026-07-03:

| Item | Value |
|---|---|
| GPU | NVIDIA GeForce RTX 3060, 12 GB VRAM (WDDM) |
| Driver / CUDA | 595.79 / CUDA 13.2 |
| torch | 2.6.0+cu124, `torch.cuda.is_available() == True` |

Re-probe with:

```bash
nvidia-smi
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

Model-phase sizing against 12 GB (see `docs/_sdd/decisions.md` D11):

- Encoder training (Phase 4) and BGE-base embeddings (Phase 5): fits easily.
- Decoder LLM (Phase 11): 7B Q4_K_M GGUF via llama.cpp (~4.7 GB) fits (per D2).
- VLM (Phase 7): Qwen2.5-VL-7B fp16 does **not** fit → int4/AWQ quantization
  or the 3B variant; decided at the Phase 7 entry gate.

Any new GPU limitation found during a phase is reported at that phase's user
gate as a re-architecture input — never silently worked around.

## E. Known environment quirks

- ffmpeg absent → video stage skips cleanly; incidents get null video.
- tiktoken absent → text chunker falls back to the whitespace tokenizer
  (the sample config pins `whitespace` explicitly).
- The browser UI test is opt-in: `RUN_BROWSER_SMOKE=1 pytest tests/ui`.
