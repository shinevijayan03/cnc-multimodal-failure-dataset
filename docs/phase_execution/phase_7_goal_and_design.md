# Phase 7 — Goal & Design (video clips + frozen VLM summaries)

User directives repeated for this phase: kill all processes (done before
coding); keep pushing real data/results/grounding into the UI; complete
integration testing.

## Decision D15 (GPU sizing, resolves the Phase-1 flag)

**Qwen/Qwen2.5-VL-3B-Instruct in bf16** on the RTX 3060. Empirical basis:
transformers 5.1.0 supports the architecture natively (no new deps); at
inference the 3B uses ~10.3 GB of the 12 GB card including the vision tower —
confirming the 7B (even int4) would not have fit alongside the display.
LLaVA-NeXT-Video comparison remains future work; the constitution's frozen
rule is architecture-level, and D15 records the 3B size substitution
necessitated by D11 hardware.

## Components

| Piece | Design |
|---|---|
| `src/vision/frames.py` | OpenCV frame sampler: N evenly spaced frames → PIL images; deterministic indices |
| `src/vision/summarizer.py` | `QwenVLSummarizer`: **FROZEN** (eval, no_grad, requires_grad False — I-1), greedy decoding (deterministic), strict-JSON prompt, robust `parse_vlm_json` (non-JSON → raw text at confidence 0.3). `TagSummarizer` fallback builds from the REAL operator tags in video_tags.csv, mode `tags_only` — can never masquerade as VLM output |
| `src/vision/build_summaries.py` | CLI → `video_summaries.parquet` (summary, labels, confidence, model, mode, frames_used per indexed clip) |
| Grounding update | `clip_summary` in every AlignedTuple now carries the real VLM/tags summary text (+ constructed-sync caveat, I-8); **`VideoClip` contract instances validated on a sample** (first producer of that contract) |
| UI | Video panel shows the real summary + label chips (mode-marked); the VIDEO timeline row's demo bars are replaced by a real summary bar whose tooltip states that content is real but the span covers the axis because sync is constructed |
| Config | `vision:` section (mode/model/device/frames/tokens); sample corpus pins `tags_only` |

## Honesty boundaries

VLM output is real model inference on the actual linked clip — but the clip
is label-matched to the incident (constructed sync), so no visual claim gets
a within-incident timestamp. That is exactly what the axis-spanning bar +
I-8 caveat express. Windowed visual events become possible only with
measured-sync footage (risk R-2, unchanged).
