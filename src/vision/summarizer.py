"""Clip summarizers — frozen VLM (I-1) + transparent tags-only fallback.

Primary: Qwen2.5-VL-3B-Instruct in bf16 on the local GPU (decisions D11/D15;
the 7B fp16 does not fit 12 GB — recorded at the Phase 1 gate). The model is
FROZEN: eval mode, no_grad, greedy decoding — no gradient ever touches it
(constitution I-1).

Fallback: `TagSummarizer` builds a summary from the REAL human-authored
regime/condition tags in video_index.parquet — clearly marked mode
"tags_only" so it can never masquerade as VLM output.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from src.vision.frames import extract_frames

QWEN_VL_MODEL = "Qwen/Qwen2.5-VL-3B-Instruct"

_PROMPT = (
    "You are inspecting frames sampled from a short CNC machining video clip. "
    "Describe the machining behavior visible across the frames. Respond with "
    "STRICT JSON only: {\"summary\": \"<one or two sentences>\", "
    "\"labels\": [\"<up to 4 short labels like normal_cut, chatter_marks, "
    "coolant_flow, tool_contact, vibration_blur>\"], "
    "\"confidence\": <0.0-1.0>}"
)


def parse_vlm_json(text: str) -> tuple[str, list[str], float]:
    """Parse the model's JSON reply; degrade to raw text at low confidence."""
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        try:
            payload = json.loads(match.group(0))
            labels = [str(x) for x in payload.get("labels", [])][:4]
            conf = float(payload.get("confidence", 0.5))
            return (str(payload.get("summary", text)).strip(), labels,
                    min(max(conf, 0.0), 1.0))
        except (ValueError, TypeError):
            pass
    return text.strip()[:300], [], 0.3          # non-JSON fallback, low confidence


@dataclass(frozen=True)
class ClipSummary:
    video_file: str
    summary: str
    visual_labels: list[str]
    confidence: float
    model: str
    mode: str                 # "vlm" | "tags_only"
    frames_used: int

    def to_dict(self) -> dict:
        return asdict(self)


class TagSummarizer:
    """Fallback built from the real video_tags.csv labels (no VLM)."""

    name = "tags_only"

    def summarize(self, video_file: str, regime: str = "unknown",
                  condition: str = "unknown") -> ClipSummary:
        return ClipSummary(
            video_file=str(video_file),
            summary=(f"Clip tagged by operator as regime={regime}, "
                     f"condition={condition} (tags-only fallback, no VLM)"),
            visual_labels=[t for t in (regime, condition) if t != "unknown"],
            confidence=0.5,
            model="video_tags.csv",
            mode="tags_only",
            frames_used=0,
        )


class QwenVLSummarizer:
    """Frozen Qwen2.5-VL on the local GPU; deterministic greedy decoding."""

    def __init__(self, model_name: str = QWEN_VL_MODEL, device: str = "cuda",
                 n_frames: int = 8, max_new_tokens: int = 160,
                 max_pixels: int = 448 * 448):
        import torch
        from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("vision.device='cuda' but no CUDA device (D11)")
        self.torch = torch
        self.name = model_name
        self.n_frames = n_frames
        self.max_new_tokens = max_new_tokens
        # Cap vision tokens per frame: uncapped 720p frames cost ~10k visual
        # tokens per clip and ran 1-3 min/clip on the RTX 3060 (found during
        # the Phase 7 bring-up); 448^2 keeps machining behavior legible while
        # cutting inference to seconds per clip.
        self.processor = AutoProcessor.from_pretrained(
            model_name, min_pixels=64 * 28 * 28, max_pixels=max_pixels)
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_name, dtype=torch.bfloat16, device_map=device)
        self.model.eval()                       # FROZEN (I-1): never trained here
        for param in self.model.parameters():
            param.requires_grad_(False)

    def summarize(self, video_file: str, regime: str = "unknown",
                  condition: str = "unknown") -> ClipSummary:
        frames = extract_frames(video_file, self.n_frames)
        if not frames:
            return TagSummarizer().summarize(video_file, regime, condition)
        messages = [{"role": "user",
                     "content": [{"type": "image"} for _ in frames]
                     + [{"type": "text", "text": _PROMPT}]}]
        prompt = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=[prompt], images=frames,
                                return_tensors="pt").to(self.model.device)
        with self.torch.no_grad():
            out = self.model.generate(**inputs, do_sample=False,
                                      max_new_tokens=self.max_new_tokens)
        generated = out[0][inputs["input_ids"].shape[1]:]
        text = self.processor.decode(generated, skip_special_tokens=True)
        summary, labels, confidence = parse_vlm_json(text)
        return ClipSummary(
            video_file=str(Path(video_file)), summary=summary,
            visual_labels=labels, confidence=confidence,
            model=self.name, mode="vlm", frames_used=len(frames))


def build_summarizer(mode: str, model_name: str = QWEN_VL_MODEL,
                     device: str = "cuda", n_frames: int = 8,
                     max_new_tokens: int = 160):
    if mode == "vlm":
        return QwenVLSummarizer(model_name=model_name, device=device,
                                n_frames=n_frames, max_new_tokens=max_new_tokens)
    if mode == "tags_only":
        return TagSummarizer()
    raise ValueError(f"unknown vision mode: {mode}")
