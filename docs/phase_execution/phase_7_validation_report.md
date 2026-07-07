# Phase 7 — Validation Report (2026-07-03)

## 1. Process hygiene

App server stopped before coding; no stray python processes.

## 2. Tests

| Suite | Result |
|---|---|
| `tests/unit/test_vision.py` (7) | JSON parser (happy/clamp/non-JSON fallback), tags-fallback determinism + real-tag content + "no VLM" marking, builder in tags mode over a synthetic index, **`VideoClip` contract accept/reject** (first producer of that contract), UI event replacement with I-8 caveat | all pass |
| Full suite | **209 passed, 1 skipped** (was 202; +7; zero broken) |
| Lint | ruff clean |

## 3. Sample corpus (fresh-clone smoke path)

`build_summaries --config config/dataset.sample.yaml` → 2 clips summarized in
`tags_only` mode (real operator tags, 0.0 s); regrounding embedded them into
all 9 tuples with **3 VideoClip contract validations**, resolution rate still
1.0, 0 chronology violations.

## 4. Real corpus (RTX 3060, Qwen2.5-VL-3B-Instruct bf16, frozen)

PENDING(vlm_run) at doc-writing time — completed results are appended to the
grounding run record in `docs/_eval/runs.jsonl` and reported at the gate:
clips summarized, mode counts, mean confidence, VRAM peak (~10.3 GB observed
during inference), regrounding metrics.

## 5. GPU report (D11/D15)

- Qwen2.5-VL-3B bf16 + vision tower peaks ~**10.3 GB of 12 GB** during
  inference on 8×720p frames — the 3B choice was necessary; 7B (even int4)
  would not have fit alongside the display.
- Model loads in ~7 s after first download; generation is greedy
  (deterministic) and gradient-free (I-1 frozen).

## 6. Constitution checklist

I-1 VLM frozen (eval + no_grad + requires_grad False; no training code path
exists) · I-2 evidence ids unchanged and still resolve-or-raise · I-6
`src/eval/` untouched · I-7 gate numbers trace to commands/run records; the
one pending number above is marked PENDING · I-8 constructed-sync caveat
embedded in every clip_summary, UI tooltip, and the VIDEO bar semantics.
