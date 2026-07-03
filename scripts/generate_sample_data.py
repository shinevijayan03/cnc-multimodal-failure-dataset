"""Generate a tiny synthetic raw-data set so a fresh clone can run the pipeline.

Writes Bosch-style tri-axial accelerometer CSVs (x/y/z at 2 kHz with Gaussian
bursts on z), two small markdown manuals, a video tag CSV, and (when ffmpeg is
on PATH) two short synthetic test clips. Everything is seeded and deterministic
except the ffmpeg clips, which are optional and skipped with --no-video.

Usage:
    python scripts/generate_sample_data.py                 # -> data_pipeline/data_raw_sample
    python -m src.cli all --config config/dataset.sample.yaml

The output directory is gitignored; this script never touches the real
data_pipeline/data_raw tree.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

DEFAULT_OUT = Path("data_pipeline/data_raw_sample")
DEFAULT_SEED = 20260702

SAMPLE_SOP_MD = """# Standard Operating Procedure — CNC Milling Cell

## 1. Setup and Workholding
Confirm the fixture and clamping force before every run. Verify workpiece
seating and check runout on the vise. Record the operation number and the
selected feed rate and spindle speed in the run sheet.

## 2. Spindle Startup
Warm up the spindle for two minutes. Listen for bearing noise and watch for
abnormal vibration or resonance during ramp-up. Abort the cycle if amplitude
exceeds the amber limit.

## 3. Cutting Operation
Monitor chip formation and coolant flow throughout the cut. Sustained chatter
or oscillation during roughing indicates an unstable depth of cut; reduce the
feed rate one step and re-check.

## 4. Abnormal Vibration Response
### 4.1 Immediate actions
Stop feed, retract the tool, and hold the spindle. Tag the incident window in
the logger.
### 4.2 Diagnosis
A sustained vibration rise preceding pressure or load instability indicates
bearing wear or tool wear progression. Inspect the tool edge for flank wear and
the spindle bearing for play before resuming.
"""

SAMPLE_MAINTENANCE_MD = """# Maintenance Manual — Milling Spindle and Toolholder

## 7. Spindle Service
### 7.1 Bearing inspection
Check the spindle bearing every 400 hours. Excessive kurtosis in the vibration
signature or a rising RMS trend between services indicates bearing wear.
Replace the bearing cartridge as a set and re-measure runout.

## 8. Tool Wear Management
Inspect inserts for flank wear and edge breakdown after each shift. A dull or
worn tool raises cutting forces, produces chatter marks, and accelerates
spindle load. Replace worn tools before the wear land exceeds 0.3 mm.

## 9. Coolant System
Verify coolant concentration and flood flow weekly. Overheating from a coolant
fault mimics tool wear symptoms; always rule out lubricant starvation first.

## 10. Clamping and Fixtures
Re-torque fixture bolts and check workholding wear monthly. Clamping loss shows
up as low-frequency oscillation and sudden amplitude steps in the accelerometer
trace.
"""


def make_burst_run(rng: np.random.Generator, fs: float, dur_s: float, burst_amp: float,
                   noise: float = 1.0, dc: float = -1015.0) -> np.ndarray:
    """Return an (n, 3) float array: x/y/z noise with one mid-run burst on z."""
    n = int(dur_s * fs)
    x = rng.normal(0.0, noise, n)
    y = rng.normal(0.0, noise, n)
    z = rng.normal(0.0, noise, n)
    if burst_amp > 0.0:
        center = rng.uniform(0.35, 0.65) * dur_s
        width = int(0.6 * fs)
        i = int(center * fs)
        z[i:i + width] += rng.normal(0.0, burst_amp, min(width, n - i))
    return np.column_stack([x, y, z + dc])


def write_sensor_csvs(root: Path, seed: int, n_good: int, n_bad: int,
                      fs: float = 2000.0, dur_s: float = 20.0) -> list[str]:
    rng = np.random.default_rng(seed)
    written = []
    for quality, count, amp in (("good", n_good, 0.0), ("bad", n_bad, 12.0)):
        folder = root / "sensor_dataset" / "M01" / "OP00" / quality
        folder.mkdir(parents=True, exist_ok=True)
        for i in range(count):
            arr = make_burst_run(rng, fs, dur_s, burst_amp=amp)
            path = folder / f"sample_{quality}_{i:02d}.csv"
            header = "x,y,z"
            np.savetxt(path, arr, delimiter=",", header=header, comments="", fmt="%.6f")
            written.append(path.as_posix())
    return written


def write_manuals(root: Path) -> list[str]:
    folder = root / "text_manuals"
    folder.mkdir(parents=True, exist_ok=True)
    sop = folder / "sample_sop.md"
    maint = folder / "sample_maintenance_manual.md"
    sop.write_text(SAMPLE_SOP_MD, encoding="utf-8")
    maint.write_text(SAMPLE_MAINTENANCE_MD, encoding="utf-8")
    return [sop.as_posix(), maint.as_posix()]


def write_videos(root: Path, no_video: bool) -> tuple[list[str], str]:
    """Write video_tags.csv always; synthesize 2 clips when ffmpeg is available."""
    folder = root / "video_raw"
    folder.mkdir(parents=True, exist_ok=True)
    tags = folder / "video_tags.csv"
    tags.write_text(
        "file,regime,condition,source\n"
        "sample_clip_00.mp4,roughing,heavy_vibration,synthetic\n"
        "sample_clip_01.mp4,idle,normal,synthetic\n",
        encoding="utf-8",
    )
    if no_video:
        return [tags.as_posix()], "skipped (--no-video)"
    if shutil.which("ffmpeg") is None:
        return [tags.as_posix()], "skipped (ffmpeg not on PATH)"
    written = [tags.as_posix()]
    for i, pattern in enumerate(("testsrc2=size=320x240:rate=30", "smptebars=size=320x240:rate=30")):
        dst = folder / f"sample_clip_{i:02d}.mp4"
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", pattern,
               "-t", "6", "-pix_fmt", "yuv420p", str(dst)]
        subprocess.run(cmd, check=True, capture_output=True)
        written.append(dst.as_posix())
    return written, "generated"


def generate(out: Path, seed: int, n_good: int, n_bad: int, no_video: bool) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    sensor_files = write_sensor_csvs(out, seed, n_good, n_bad)
    manual_files = write_manuals(out)
    video_files, video_status = write_videos(out, no_video)
    return {
        "out": out.as_posix(),
        "seed": seed,
        "sensor_files": sensor_files,
        "manual_files": manual_files,
        "video_files": video_files,
        "video_status": video_status,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic sample raw data.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--n-good", type=int, default=4)
    parser.add_argument("--n-bad", type=int, default=4)
    parser.add_argument("--no-video", action="store_true",
                        help="Skip ffmpeg clip synthesis (tags CSV is still written)")
    args = parser.parse_args(argv)
    summary = generate(args.out, args.seed, args.n_good, args.n_bad, args.no_video)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
