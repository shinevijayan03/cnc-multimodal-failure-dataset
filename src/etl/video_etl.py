"""Stage 3 — Video ETL.

Discovers raw MP4s, normalizes them to 720p/30fps/H.264 via ffmpeg, merges
human regime/condition tags, and writes ``video_index.parquet``. All ffmpeg use
is wrapped so it can be mocked in unit tests and isolated when ffmpeg is missing.
See ``docs/software_design.md`` §7.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pandas as pd

from ..common.config import PipelineConfig, VideoNormalizeCfg
from ..common.errors import VideoToolError
from ..common.ids import video_id
from ..common.io_utils import rows_to_df, write_parquet_atomic
from ..common.logging_utils import RunSummary, get_logger
from ..common.schemas import Condition, Regime, VideoIndexRow

_INSTALL_HINT = ("ffmpeg/ffprobe not found on PATH. Install from https://ffmpeg.org/ "
                 "(Windows: `winget install Gyan.FFmpeg`) and re-run the video stage.")


# --------------------------------------------------------------------------- #
# ffprobe
# --------------------------------------------------------------------------- #
def parse_probe(probe_json: str) -> dict:
    """Pure parser: ffprobe JSON -> {fps, duration_s, codec, width, height}."""
    data = json.loads(probe_json)
    streams = data.get("streams", [])
    vstream = next((s for s in streams if s.get("codec_type") == "video"), None) or \
        (streams[0] if streams else {})
    # fps comes as a "num/den" string (avg_frame_rate / r_frame_rate).
    fps = 0.0
    for key in ("avg_frame_rate", "r_frame_rate"):
        rate = vstream.get(key)
        if rate and rate != "0/0":
            num, _, den = rate.partition("/")
            den_f = float(den) if den else 1.0
            if den_f:
                fps = float(num) / den_f
                break
    duration = vstream.get("duration") or data.get("format", {}).get("duration")
    return {
        "fps": round(fps, 6),
        "duration_s": float(duration) if duration else 0.0,
        "codec": vstream.get("codec_name", "unknown"),
        "width": int(vstream.get("width", 0) or 0),
        "height": int(vstream.get("height", 0) or 0),
    }


class FfprobeReader:
    def __init__(self, ffprobe_path: str = "ffprobe"):
        self.ffprobe_path = ffprobe_path

    def _run_ffprobe(self, path: Path) -> str:
        args = [self.ffprobe_path, "-v", "error", "-show_entries",
                "stream=codec_type,codec_name,avg_frame_rate,r_frame_rate,width,height,duration:"
                "format=duration", "-of", "json", str(path)]
        try:
            proc = subprocess.run(args, capture_output=True, text=True, check=False)
        except FileNotFoundError as exc:
            raise VideoToolError(_INSTALL_HINT) from exc
        if proc.returncode != 0:
            raise VideoToolError(f"ffprobe failed on {path}: {proc.stderr.strip()}")
        return proc.stdout

    def probe(self, path: Path) -> dict:
        return parse_probe(self._run_ffprobe(path))


# --------------------------------------------------------------------------- #
# ffmpeg normalize
# --------------------------------------------------------------------------- #
class FfmpegNormalizer:
    def __init__(self, cfg: VideoNormalizeCfg, probe: FfprobeReader | None = None):
        self.cfg = cfg
        self.probe = probe or FfprobeReader()

    def is_conformant(self, info: dict) -> bool:
        return (info.get("height") == self.cfg.target_height
                and abs(info.get("fps", 0) - self.cfg.target_fps) < 0.5
                and info.get("codec") in ("h264", "libx264"))

    def build_command(self, src: Path, dst: Path) -> list[str]:
        return [
            self.cfg.ffmpeg_path, "-y", "-i", str(src),
            "-vf", f"scale=-2:{self.cfg.target_height},fps={self.cfg.target_fps}",
            "-c:v", self.cfg.target_codec, "-pix_fmt", "yuv420p",
            "-an", "-movflags", "+faststart", str(dst),
        ]

    def normalize(self, src: Path, dst: Path, info: dict | None = None) -> dict:
        """Normalize *src* to *dst*; skip (copy) if already conformant.

        Returns the probe info dict for *dst*. Raises VideoToolError on failure.
        """
        info = info if info is not None else self.probe.probe(src)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if self.is_conformant(info) and not self.cfg.overwrite:
            if src.resolve() != dst.resolve():
                shutil.copy2(src, dst)
            return info
        args = self.build_command(src, dst)
        try:
            proc = subprocess.run(args, capture_output=True, text=True, check=False)
        except FileNotFoundError as exc:
            raise VideoToolError(_INSTALL_HINT) from exc
        if proc.returncode != 0:
            raise VideoToolError(f"ffmpeg failed on {src}: {proc.stderr.strip()[:500]}")
        return self.probe.probe(dst)


# --------------------------------------------------------------------------- #
# Tag merge
# --------------------------------------------------------------------------- #
class TagMerger:
    """Merge human-authored regime/condition/source tags from a CSV."""

    def __init__(self, tags_csv: pd.DataFrame | None):
        self.by_key: dict[str, dict] = {}
        if tags_csv is not None and not tags_csv.empty:
            for _, r in tags_csv.iterrows():
                row = {k: r[k] for k in tags_csv.columns}
                for key_col in ("video_id", "video_file", "file", "filename", "clip"):
                    if key_col in row and pd.notna(row[key_col]):
                        self.by_key[Path(str(row[key_col])).name] = row
                        self.by_key[str(row[key_col])] = row

    def merge(self, lookup_keys: list[str]) -> tuple[Regime, Condition, str]:
        row = next((self.by_key[k] for k in lookup_keys if k in self.by_key), None)
        if row is None:
            return Regime.unknown, Condition.unknown, "unknown"
        regime = self._enum(Regime, row.get("regime") or row.get("regime_label"))
        condition = self._enum(Condition, row.get("condition") or row.get("condition_label"))
        source = str(row.get("source") or "unknown")
        return regime, condition, source

    @staticmethod
    def _enum(enum_cls, value):
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return enum_cls.unknown
        try:
            return enum_cls(str(value).strip().lower())
        except ValueError:
            return enum_cls.unknown


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
class VideoETL:
    def __init__(self, cfg: PipelineConfig, logger=None):
        self.cfg = cfg
        self.log = logger or get_logger("video", cfg.runtime.log_level, cfg.runtime.log_format)
        self.probe = FfprobeReader(cfg.video.normalize.ffmpeg_path.replace("ffmpeg", "ffprobe"))
        self.normalizer = FfmpegNormalizer(cfg.video.normalize, self.probe)

    def _discover(self) -> list[Path]:
        root = Path(self.cfg.paths.raw_video_root)
        if not root.exists():
            return []
        return sorted(p for p in root.rglob("*.mp4") if p.is_file())

    def _load_tags(self) -> TagMerger:
        csv_path = self.cfg.resolve(self.cfg.video.tagging_csv)
        if Path(csv_path).exists():
            try:
                return TagMerger(pd.read_csv(csv_path))
            except Exception as exc:  # noqa: BLE001
                self.log.warning("could not read tagging csv", extra={"error": str(exc)})
        return TagMerger(None)

    def _tools_available(self) -> bool:
        ffmpeg = self.cfg.video.normalize.ffmpeg_path
        ffprobe = ffmpeg.replace("ffmpeg", "ffprobe")
        return shutil.which(ffmpeg) is not None and shutil.which(ffprobe) is not None

    def run(self, limit: int | None = None, dry_run: bool | None = None) -> RunSummary:
        dry_run = self.cfg.runtime.dry_run if dry_run is None else dry_run
        summ = RunSummary(stage="video", dry_run=dry_run)
        files = self._discover()
        summ.discovered = len(files)

        if not self._tools_available():
            # Isolated, graceful: skip the whole stage with one clear hint so
            # `all` can proceed (assembly tolerates an empty video index).
            self.log.warning("video stage skipped: " + _INSTALL_HINT,
                             extra={"clips_found": len(files)})
            summ.skipped = len(files)
            summ.note("reason", "ffmpeg_missing")
            return summ

        tags = self._load_tags()
        video_dir = Path(self.cfg.paths.video_dir)
        rows: list[VideoIndexRow] = []
        nmin, nmax = self.cfg.video.normalize.clip_min_s, self.cfg.video.normalize.clip_max_s
        flagged = 0

        for path in files:
            if limit is not None and summ.processed >= limit:
                break
            rel = path.relative_to(Path(self.cfg.paths.raw_video_root)).as_posix()
            keys = [rel, path.name, path.stem]
            regime, condition, source = tags.merge(keys)
            vid = video_id(source, rel)
            try:
                if dry_run:
                    info = self.probe.probe(path)
                    out_rel = None
                else:
                    dst = video_dir / f"{vid}.mp4"
                    info = self.normalizer.normalize(path, dst)
                    out_rel = f"{Path(self.cfg.paths.data_processed).name}/{video_dir.name}/{vid}.mp4"
            except VideoToolError as exc:
                summ.bump("errors")
                self.log.warning("clip failed", extra={"clip": rel, "error": str(exc)})
                if self.cfg.runtime.fail_fast:
                    raise
                continue
            if not (nmin <= info["duration_s"] <= nmax):
                flagged += 1
            row = VideoIndexRow(
                video_id=vid,
                video_file=out_rel or str(path),
                video_fps=info["fps"],
                duration_s=info["duration_s"],
                regime_label=regime,
                condition_label=condition,
                source=source,
            )
            rows.append(row)
            summ.bump("processed")
            if not dry_run:
                summ.bump("written")

        if not dry_run and rows:
            write_parquet_atomic(rows_to_df(rows), self.cfg.paths.video_index)
            self.log.info("video index written",
                          extra={"path": self.cfg.paths.video_index, "rows": len(rows)})
        summ.note("duration_flagged", flagged)
        return summ
