"""Frame extraction for VLM clip summarization (Build Phase 7).

Uses OpenCV (already installed) to sample N evenly spaced frames from a clip.
Deterministic: same file + same n -> same frame indices.
"""

from __future__ import annotations

from pathlib import Path


def extract_frames(video_path: str | Path, n_frames: int = 8) -> list:
    """Return up to *n_frames* evenly spaced PIL images from the clip."""
    import cv2
    from PIL import Image

    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"video not found: {path}")
    cap = cv2.VideoCapture(str(path))
    try:
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total <= 0:
            return []
        step = max(1, total // n_frames)
        indices = list(range(0, total, step))[:n_frames]
        frames = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok:
                continue
            frames.append(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
        return frames
    finally:
        cap.release()
