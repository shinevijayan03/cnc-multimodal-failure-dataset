"""Stage 1 — Sensor ETL.

Turns raw vibration logs into windowed incidents plus a ``sensor_windows.parquet``
index. The numeric core (`FsEstimator`, `EventDetector`, `WindowCarver`,
`EvidenceSpanExtractor`) is pure (arrays + config, no IO) so it is unit-tested
with synthetic signals. See ``docs/software_design.md`` §5.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator

import numpy as np
import pandas as pd

from ..common.config import (
    EventDetectionCfg,
    EvidenceSpansCfg,
    FsEstimationCfg,
    PipelineConfig,
    SensorCfg,
    SensorDatasetCfg,
    WindowingCfg,
)
from ..common.errors import ReaderError
from ..common.ids import incident_id
from ..common.io_utils import exists_and_fresh, rows_to_df, write_parquet_atomic
from ..common.logging_utils import RunSummary, get_logger
from ..common.schemas import FailureFamily, SensorWindowRow, Span


# --------------------------------------------------------------------------- #
# Small value objects
# --------------------------------------------------------------------------- #
@dataclass
class RawRun:
    run_id: str
    df: pd.DataFrame
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Event:
    t_event_s: float          # time of peak detection statistic
    t_start_s: float          # start of the above-threshold interval
    t_end_s: float            # end of the above-threshold interval
    score: float


@dataclass
class Window:
    df: pd.DataFrame          # carved slice with time_s + t_rel_s + channels
    window_start_s: float     # original-run time
    window_end_s: float
    t_event_s: float
    n_samples: int


# --------------------------------------------------------------------------- #
# Readers (extensibility hook #1)
# --------------------------------------------------------------------------- #
_QUALITY_DIRS = {"good", "bad", "ok", "nok"}


def read_generic_csv(root: Path, dscfg: SensorDatasetCfg, logger) -> Iterator[RawRun]:
    """Yield one RawRun per CSV found under *root* (recursively).

    The immediate parent folder name, when it is a quality label (good/bad), is
    surfaced as ``meta['quality']`` for downstream label derivation.
    """
    if not root.exists():
        logger.warning("sensor reader: path does not exist, skipping dataset",
                       extra={"dataset": dscfg.name, "path": str(root)})
        return
    files = sorted(p for p in root.rglob("*.csv") if p.is_file())
    for f in files:
        rel = f.relative_to(root).as_posix()
        quality = f.parent.name.lower() if f.parent.name.lower() in _QUALITY_DIRS else None
        try:
            df = pd.read_csv(f)
        except Exception as exc:  # noqa: BLE001 - per-file robustness: skip, don't abort
            logger.warning("could not read CSV, skipping file",
                           extra={"file": str(f), "error": str(exc)})
            continue
        yield RawRun(run_id=rel, df=df, meta={"quality": quality, "source_file": str(f)})


def read_bosch_h5(root: Path, dscfg: SensorDatasetCfg, logger) -> Iterator[RawRun]:
    """Yield one RawRun per HDF5 file (Bosch CNC layout).

    Defensive: tries a couple of common dataset names for the tri-axial array.
    Raises ReaderError on an unrecognized layout so the run is skipped+counted.
    """
    if not root.exists():
        logger.warning("sensor reader: path does not exist, skipping dataset",
                       extra={"dataset": dscfg.name, "path": str(root)})
        return
    files = sorted(p for p in root.rglob("*.h5") if p.is_file())
    if not files:  # nothing staged -> no h5py needed
        return
    try:
        import h5py  # noqa: PLC0415 - optional dependency, imported lazily
    except ImportError as exc:
        raise ReaderError(
            "reader 'bosch_h5' requires h5py (pip install h5py)"
        ) from exc
    for f in files:
        rel = f.relative_to(root).as_posix()
        with h5py.File(f, "r") as h5:
            arr = None
            for key in ("vibration_data", "data", "X", "accel"):
                if key in h5:
                    arr = np.asarray(h5[key])
                    break
            if arr is None or arr.ndim != 2 or arr.shape[1] < 3:
                raise ReaderError(f"unrecognized HDF5 layout in {f}")
            df = pd.DataFrame(arr[:, :3], columns=["x", "y", "z"])
            meta = {k: h5.attrs[k] for k in h5.attrs.keys()}
        yield RawRun(run_id=rel, df=df, meta=meta)


READERS: dict[str, Callable[..., Iterator[RawRun]]] = {
    "generic_csv": read_generic_csv,
    "bosch_h5": read_bosch_h5,
}


# --------------------------------------------------------------------------- #
# Normalizer
# --------------------------------------------------------------------------- #
class Normalizer:
    def __init__(self, cfg: SensorCfg):
        self.cfg = cfg

    def rename_and_select(self, df: pd.DataFrame, column_map: dict[str, str]) -> pd.DataFrame:
        """Rename source columns to canonical names and drop everything unmapped.

        Keeps only the canonical channels and any optional channels that are
        present (plus ``time_s`` if it survives the rename). Coerces to float.
        """
        out = df.rename(columns=dict(column_map)) if column_map else df.copy()
        keep_order = ["time_s"] + [c for c in self.cfg.canonical_channels if c != "time_s"]
        keep_order += list(self.cfg.optional_channels)
        cols = [c for c in keep_order if c in out.columns]
        out = out[cols].copy()
        for c in cols:
            out[c] = pd.to_numeric(out[c], errors="coerce")
        return out

    def build_time(self, df: pd.DataFrame, fs_hz: float) -> pd.DataFrame:
        """Ensure a strictly-increasing ``time_s`` column.

        If a usable monotonic ``time_s`` already exists it is kept; otherwise
        (missing, non-monotonic, or duplicated) it is reconstructed uniformly
        from *fs_hz*.
        """
        df = df.copy()
        n = len(df)
        existing = df["time_s"].to_numpy() if "time_s" in df.columns else None
        usable = (
            existing is not None
            and np.all(np.isfinite(existing))
            and np.all(np.diff(existing) > 0)
        )
        if not usable:
            df["time_s"] = np.arange(n, dtype="float64") / float(fs_hz)
        # Reorder canonical-first.
        order = ["time_s"] + [c for c in df.columns if c != "time_s"]
        return df[order]

    def normalize(self, run: RawRun, column_map: dict[str, str], fs_hz: float) -> pd.DataFrame:
        """Convenience: rename+select then build/repair time from *fs_hz*."""
        return self.build_time(self.rename_and_select(run.df, column_map), fs_hz)


# --------------------------------------------------------------------------- #
# FsEstimator
# --------------------------------------------------------------------------- #
class FsEstimator:
    def __init__(self, cfg: FsEstimationCfg):
        self.cfg = cfg

    def _validate(self, fs: float) -> float:
        if not np.isfinite(fs) or fs <= 0:
            raise ReaderError(f"estimated fs_hz is non-positive/non-finite: {fs}")
        if not (self.cfg.min_plausible_hz <= fs <= self.cfg.max_plausible_hz):
            raise ReaderError(
                f"estimated fs_hz {fs:.3f} outside plausible range "
                f"[{self.cfg.min_plausible_hz}, {self.cfg.max_plausible_hz}]"
            )
        return fs

    def estimate(self, df: pd.DataFrame, meta: dict, fs_hz: float | None = None) -> float:
        """Return the sampling rate in Hz.

        Precedence: an explicit dataset-level ``fs_hz`` override always wins;
        otherwise the configured method is used (median_dt | metadata | fixed).
        """
        if fs_hz is not None:
            return self._validate(float(fs_hz))
        method = self.cfg.method
        if method == "metadata":
            if "fs_hz" in meta and meta["fs_hz"]:
                return self._validate(float(meta["fs_hz"]))
            raise ReaderError("fs_estimation.method='metadata' but no fs_hz in run meta")
        if method == "fixed":
            raise ReaderError("fs_estimation.method='fixed' but no dataset fs_hz provided")
        # default: median_dt
        if "time_s" not in df.columns:
            raise ReaderError("fs_estimation.method='median_dt' but no time_s column")
        t = df["time_s"].to_numpy()
        dt = np.diff(t)
        dt = dt[np.isfinite(dt) & (dt > 0)]
        if dt.size == 0:
            raise ReaderError("cannot estimate fs: no positive time deltas")
        return self._validate(1.0 / float(np.median(dt)))


# --------------------------------------------------------------------------- #
# EventDetector
# --------------------------------------------------------------------------- #
class EventDetector:
    def __init__(self, cfg: EventDetectionCfg):
        self.cfg = cfg

    def _energy_channel(self, df: pd.DataFrame) -> np.ndarray:
        ch = self.cfg.channel_for_energy
        if ch == "magnitude":
            accel = [c for c in ("ax", "ay", "az") if c in df.columns]
            x = np.sqrt(np.sum([df[c].to_numpy() ** 2 for c in accel], axis=0))
        elif ch in df.columns:
            x = df[ch].to_numpy(dtype="float64")
        else:  # fall back to first available accel channel
            for cand in ("az", "ay", "ax"):
                if cand in df.columns:
                    x = df[cand].to_numpy(dtype="float64")
                    break
            else:
                raise ReaderError("no usable channel for event detection")
        x = x.astype("float64")
        x = np.nan_to_num(x, nan=float(np.nanmean(x)) if np.any(np.isfinite(x)) else 0.0)
        return x - float(np.mean(x))  # remove DC / mounting offset before RMS

    def _sliding_rms(self, x: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray]:
        win = max(1, int(round(self.cfg.window_s * fs)))
        hop = max(1, int(round(self.cfg.hop_s * fs)))
        if x.size < win:
            return np.empty(0), np.empty(0)
        x2 = x.astype("float64") ** 2
        csum = np.concatenate([[0.0], np.cumsum(x2)])
        starts = np.arange(0, x.size - win + 1, hop)
        rms = np.sqrt((csum[starts + win] - csum[starts]) / win)
        centers = (starts + win // 2) / fs
        return rms, centers

    def detect(self, df: pd.DataFrame, fs_hz: float, cfg: EventDetectionCfg | None = None
               ) -> list[Event]:
        cfg = cfg or self.cfg
        if cfg.method == "segment_center":
            t = df["time_s"].to_numpy()
            if t.size == 0:
                return []
            t_start = float(t[0])
            t_end = float(t[-1])
            return [Event(
                t_event_s=(t_start + t_end) / 2.0,
                t_start_s=t_start,
                t_end_s=t_end,
                score=1.0,
            )]

        x = self._energy_channel(df)
        rms, centers = self._sliding_rms(x, fs_hz)
        if rms.size == 0:
            return []

        if cfg.threshold_kind == "zscore":
            base_n = max(1, int(round(cfg.baseline_window_s / cfg.hop_s)))
            s = pd.Series(rms)
            # Robust baseline: median + IQR-derived scale. A short burst barely
            # moves the median or quartiles, so the event does not contaminate
            # its own baseline (a plain centered mean/std would hide it).
            base_mu = s.rolling(base_n, min_periods=1, center=True).median().to_numpy()
            base_lo = s.rolling(base_n, min_periods=1, center=True).quantile(0.10).to_numpy()
            # One-sided robust scale from the LOWER tail only: vibration events are
            # positive RMS excursions, so median & q10 stay in the quiet regime even
            # when the event fills a large fraction of the baseline window. q10 is
            # ~-1.2816 sigma below the median for a gaussian.
            base_sd = (base_mu - base_lo) / 1.2816
            global_sd = ((np.nanmedian(rms) - np.nanquantile(rms, 0.10)) / 1.2816
                         or np.nanstd(rms) or 1.0)
            base_sd = np.where((base_sd > 0) & np.isfinite(base_sd), base_sd, global_sd)
            stat = (rms - base_mu) / base_sd
            thr = cfg.threshold_value
        elif cfg.threshold_kind == "quantile":
            stat = rms
            thr = float(np.nanquantile(rms, cfg.threshold_value))
        else:  # absolute
            stat = rms
            thr = cfg.threshold_value

        above = np.asarray(stat > thr)
        runs = self._contiguous_runs(above)
        events: list[Event] = []
        for i0, i1 in runs:  # inclusive index range over the rms grid
            t_start, t_end = float(centers[i0]), float(centers[i1])
            seg = stat[i0:i1 + 1]
            pk = int(np.argmax(seg)) + i0
            events.append(Event(t_event_s=float(centers[pk]), t_start_s=t_start,
                                 t_end_s=t_end, score=float(stat[pk])))

        events = self._merge(events, cfg.min_event_separation_s)
        events = [e for e in events if (e.t_end_s - e.t_start_s) >= cfg.min_event_duration_s
                  or cfg.min_event_duration_s == 0]
        return events

    @staticmethod
    def _contiguous_runs(mask: np.ndarray) -> list[tuple[int, int]]:
        if not mask.any():
            return []
        idx = np.flatnonzero(mask)
        splits = np.flatnonzero(np.diff(idx) > 1)
        groups = np.split(idx, splits + 1)
        return [(int(g[0]), int(g[-1])) for g in groups]

    @staticmethod
    def _merge(events: list[Event], min_sep_s: float) -> list[Event]:
        if not events:
            return []
        events = sorted(events, key=lambda e: e.t_start_s)
        merged = [events[0]]
        for e in events[1:]:
            last = merged[-1]
            if e.t_start_s - last.t_end_s < min_sep_s:
                # merge; keep the higher-scoring peak as the event time
                t_end = max(last.t_end_s, e.t_end_s)
                if e.score > last.score:
                    peak_t, peak_s = e.t_event_s, e.score
                else:
                    peak_t, peak_s = last.t_event_s, last.score
                merged[-1] = Event(t_event_s=peak_t, t_start_s=last.t_start_s,
                                   t_end_s=t_end, score=peak_s)
            else:
                merged.append(e)
        return merged


# --------------------------------------------------------------------------- #
# WindowCarver
# --------------------------------------------------------------------------- #
class WindowCarver:
    def carve(self, df: pd.DataFrame, event: Event, fs_hz: float, cfg: WindowingCfg
              ) -> Window | None:
        t0 = event.t_event_s - cfg.pre_event_s
        t1 = event.t_event_s + cfg.post_event_s
        t = df["time_s"].to_numpy()
        partial = (t0 < t.min() - 1e-9) or (t1 > t.max() + 1e-9)
        if partial and cfg.drop_partial_windows:
            return None
        mask = (t >= t0) & (t <= t1)
        sl = df.loc[mask].copy()
        if sl.empty:
            return None
        sl.insert(1, "t_rel_s", sl["time_s"].to_numpy() - event.t_event_s)
        return Window(
            df=sl,
            window_start_s=float(sl["time_s"].iloc[0]),
            window_end_s=float(sl["time_s"].iloc[-1]),
            t_event_s=event.t_event_s,
            n_samples=len(sl),
        )


# --------------------------------------------------------------------------- #
# EvidenceSpanExtractor
# --------------------------------------------------------------------------- #
class EvidenceSpanExtractor:
    def __init__(self, cfg: EvidenceSpansCfg):
        self.cfg = cfg

    def extract(self, window: Window, event: Event, cfg: EvidenceSpansCfg | None = None
                ) -> list[Span]:
        cfg = cfg or self.cfg
        rel_min = float(window.df["t_rel_s"].iloc[0])
        rel_max = float(window.df["t_rel_s"].iloc[-1])
        # threshold_crossings (default): the detected interval, in incident-relative time.
        start = (event.t_start_s - event.t_event_s) - cfg.pad_s
        end = (event.t_end_s - event.t_event_s) + cfg.pad_s
        start = max(start, rel_min)
        end = min(end, rel_max)
        if end < start:
            return []
        return [Span(start_s=start, end_s=end)][: cfg.max_spans]


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def _maybe_resample(df: pd.DataFrame, fs: float, target: float | None
                    ) -> tuple[pd.DataFrame, float]:
    if target is None or abs(target - fs) < 1e-6:
        return df, fs
    t = df["time_s"].to_numpy()
    duration = t[-1] - t[0]
    new_n = max(2, int(round(duration * target)))
    new_t = t[0] + np.arange(new_n) / target
    out = {"time_s": new_t}
    for c in df.columns:
        if c == "time_s":
            continue
        out[c] = np.interp(new_t, t, df[c].to_numpy())
    return pd.DataFrame(out), target


class SensorETL:
    def __init__(self, cfg: PipelineConfig, logger=None):
        self.cfg = cfg
        self.log = logger or get_logger("sensor", cfg.runtime.log_level, cfg.runtime.log_format)
        s = cfg.sensor
        self.normalizer = Normalizer(s)
        self.fs_estimator = FsEstimator(s.fs_estimation)
        self.detector = EventDetector(s.event_detection)
        self.carver = WindowCarver()
        self.spanner = EvidenceSpanExtractor(s.evidence_spans)

    def _repo_relative(self, path: Path) -> str:
        root = Path(self.cfg.repo_root) if self.cfg.repo_root else Path.cwd()
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return str(path)

    def run(self, limit: int | None = None, dry_run: bool | None = None) -> RunSummary:
        dry_run = self.cfg.runtime.dry_run if dry_run is None else dry_run
        summ = RunSummary(stage="sensor", dry_run=dry_run)
        rows: list[SensorWindowRow] = []
        windows_dir = Path(self.cfg.paths.sensor_windows_dir)
        s = self.cfg.sensor

        for dscfg in s.datasets:
            if not dscfg.enabled:
                self.log.info("dataset disabled, skipping", extra={"dataset": dscfg.name})
                summ.bump("skipped")
                continue
            reader = READERS.get(dscfg.reader)
            if reader is None:
                self.log.error("unknown reader", extra={"dataset": dscfg.name,
                                                        "reader": dscfg.reader})
                summ.bump("errors")
                if self.cfg.runtime.fail_fast:
                    raise ReaderError(f"unknown reader '{dscfg.reader}'")
                continue
            root = self.cfg.resolve(dscfg.path)
            try:
                run_iter = reader(root, dscfg, self.log)
                for run in run_iter:
                    if limit is not None and summ.processed >= limit:
                        break
                    try:
                        n_win = self._process_run(run, dscfg, rows, windows_dir, dry_run, summ)
                        summ.bump("processed")
                        self.log.info("run processed", extra={"dataset": dscfg.name,
                                                              "run": run.run_id, "windows": n_win})
                    except Exception as exc:  # noqa: BLE001 - one bad run never aborts the stage
                        summ.bump("errors")
                        self.log.warning("run failed, skipped",
                                         extra={"dataset": dscfg.name, "run": run.run_id,
                                                "error": str(exc)})
                        if self.cfg.runtime.fail_fast:
                            raise
            except Exception as exc:  # noqa: BLE001 - dataset-level reader failure
                summ.bump("errors")
                self.log.warning("reader failed, skipping dataset",
                                 extra={"dataset": dscfg.name, "error": str(exc)})
                if self.cfg.runtime.fail_fast:
                    raise
            if limit is not None and summ.processed >= limit:
                break

        if not dry_run and rows:
            write_parquet_atomic(rows_to_df(rows), self.cfg.paths.sensor_index)
            self.log.info("sensor index written", extra={"path": self.cfg.paths.sensor_index,
                                                         "rows": len(rows)})
        summ.note("incident_hours",
                  round(sum((r.window_end_s - r.window_start_s) for r in rows) / 3600, 4))
        return summ

    def _process_run(self, run: RawRun, dscfg: SensorDatasetCfg, rows: list[SensorWindowRow],
                     windows_dir: Path, dry_run: bool, summ: RunSummary) -> int:
        s = self.cfg.sensor
        df_r = self.normalizer.rename_and_select(run.df, dscfg.column_map)
        if not any(c in df_r.columns for c in ("ax", "ay", "az")):
            raise ReaderError(f"no canonical accel channels after column_map for {run.run_id}")
        fs = self.fs_estimator.estimate(df_r, run.meta, dscfg.fs_hz)
        df = self.normalizer.build_time(df_r, fs)
        df, fs = _maybe_resample(df, fs, s.fs_estimation.resample_to_hz)

        events = self.detector.detect(df, fs, s.event_detection)
        if s.windowing.max_windows_per_run is not None:
            events = events[: s.windowing.max_windows_per_run]

        channels = [c for c in df.columns if c not in ("time_s", "t_rel_s")]
        n_written = 0
        for ev in events:
            window = self.carver.carve(df, ev, fs, s.windowing)
            if window is None:
                summ.bump("skipped")
                continue
            spans = self.spanner.extract(window, ev, s.evidence_spans)
            inc_id = incident_id(dscfg.name, run.run_id, ev.t_event_s)
            out_path = windows_dir / f"{inc_id}.parquet"
            sensor_file = self._repo_relative(out_path)
            row = SensorWindowRow(
                incident_id=inc_id,
                source_dataset=dscfg.name,
                machine_family=dscfg.machine_family,
                failure_family=FailureFamily.unknown,
                window_start_s=window.window_start_s,
                window_end_s=window.window_end_s,
                fs_hz=fs,
                sensor_file=sensor_file,
                sensor_channels=channels,
                sensor_relevant_spans=spans,
                n_samples=window.n_samples,
            )
            rows.append(row)
            if not dry_run:
                src = Path(run.meta.get("source_file", "")) if run.meta.get("source_file") else None
                if src and exists_and_fresh(out_path, src):
                    summ.bump("skipped")  # idempotent: already built from same source
                else:
                    write_parquet_atomic(window.df, out_path)
            summ.bump("written")
            n_written += 1
        return n_written
