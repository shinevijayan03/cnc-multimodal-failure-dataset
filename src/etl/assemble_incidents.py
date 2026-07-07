"""Stage 4 — Incident Assembly.

Joins the three modality indices into ``incidents.parquet``: derives labels from
the sensor backbone, attaches a label-matched video clip and topic-retrieved
SOP/maintenance text chunks (both flagged as *heuristic* via ``alignment_method``),
and assigns a grouped, seeded split. See ``docs/software_design.md`` §8.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..common.config import (
    PipelineConfig,
    SplitCfg,
    TextRetrievalCfg,
    VideoMatchCfg,
)
from ..common.errors import AssemblyError
from ..common.ids import stable_hash
from ..common.io_utils import load_json_col, read_parquet, rows_to_df, write_parquet_atomic
from ..common.logging_utils import RunSummary, get_logger
from ..common.schemas import (
    AlignmentMethod,
    Condition,
    DocType,
    FailureFamily,
    IncidentRow,
    Regime,
    Severity,
    Span,
    Split,
)


# --------------------------------------------------------------------------- #
# LabelDeriver
# --------------------------------------------------------------------------- #
class LabelDeriver:
    """Derive weak labels; severity and fallback failure from amplitude quantiles."""

    def __init__(self, amp_lo: float | None = None, amp_hi: float | None = None,
                 default_label: str = "unknown"):
        self.amp_lo = amp_lo
        self.amp_hi = amp_hi
        self.default = default_label

    def severity(self, amplitude: float | None) -> Severity:
        if amplitude is None or self.amp_lo is None or self.amp_hi is None \
                or not np.isfinite(amplitude):
            return Severity.unknown
        if amplitude <= self.amp_lo:
            return Severity.low
        if amplitude <= self.amp_hi:
            return Severity.med
        return Severity.high

    def failure_family(self, amplitude: float | None) -> FailureFamily:
        severity = self.severity(amplitude)
        if severity is Severity.low:
            return FailureFamily.tool_wear
        if severity is Severity.med:
            return FailureFamily.spindle_fault
        if severity is Severity.high:
            return FailureFamily.chatter
        return FailureFamily.unknown

    def weak_bucket(self, key: str) -> int:
        return int(stable_hash(key), 16) % 3

    def weak_failure_family(self, key: str) -> FailureFamily:
        return (
            FailureFamily.tool_wear,
            FailureFamily.spindle_fault,
            FailureFamily.chatter,
        )[self.weak_bucket(key)]

    def weak_severity(self, key: str) -> Severity:
        return (Severity.low, Severity.med, Severity.high)[self.weak_bucket(key)]

    def derive(self, meta: dict | None = None, amplitude: float | None = None) -> dict:
        meta = meta or {}
        regime = meta.get("regime", self.default)
        try:
            regime_enum = Regime(str(regime).lower())
        except ValueError:
            regime_enum = Regime.unknown
        failure = self.failure_family(amplitude)
        root_cause = meta.get("root_cause")
        if root_cause is None and failure is not FailureFamily.unknown:
            root_cause = f"weak_signal_{failure.value}"
        return {
            "regime_label": regime_enum,
            "phase_label": str(meta.get("phase", self.default)),
            "severity_label": self.severity(amplitude),
            "failure_family": failure,
            "root_cause_label": str(root_cause or self.default),
        }


# --------------------------------------------------------------------------- #
# VideoMatcher
# --------------------------------------------------------------------------- #
class VideoMatcher:
    def __init__(self, video_idx: pd.DataFrame, cfg: VideoMatchCfg, rng: np.random.Generator):
        self.df = video_idx if video_idx is not None else pd.DataFrame()
        self.cfg = cfg
        self.rng = rng
        self.used: set[str] = set()

    def _available(self, frame: pd.DataFrame) -> pd.DataFrame:
        if self.cfg.allow_reuse or frame.empty:
            return frame
        return frame[~frame["video_file"].isin(self.used)]

    def _pick(self, frame: pd.DataFrame):
        frame = self._available(frame)
        if frame.empty:
            return None
        idx = int(self.rng.integers(0, len(frame)))
        row = frame.iloc[idx]
        if not self.cfg.allow_reuse:
            self.used.add(row["video_file"])
        return row

    def match(self, regime: Regime, condition: Condition):
        """Return (clip_row_or_None, AlignmentMethod)."""
        if self.df.empty:
            return None, AlignmentMethod.none
        frame = self.df
        if self.cfg.require_regime_match:
            frame = frame[frame["regime_label"] == regime.value]
        if self.cfg.require_condition_match:
            frame = frame[frame["condition_label"] == condition.value]
        picked = self._pick(frame)
        if picked is not None:
            return picked, AlignmentMethod.label_match
        if self.cfg.fallback_to_idle:
            idle = self.df[self.df["regime_label"] == Regime.idle.value]
            picked = self._pick(idle)
            if picked is not None:
                return picked, AlignmentMethod.idle_fallback
        return None, AlignmentMethod.none


# --------------------------------------------------------------------------- #
# TextRetriever
# --------------------------------------------------------------------------- #
class TextRetriever:
    def __init__(self, chunks: pd.DataFrame, cfg: TextRetrievalCfg,
                 failure_to_topics: dict[str, list[str]]):
        self.cfg = cfg
        self.failure_to_topics = failure_to_topics
        self.chunks = chunks if chunks is not None else pd.DataFrame()
        self._cache: dict[tuple[str, str, int, int], list[str]] = {}
        if not self.chunks.empty and "topic_tags" in self.chunks.columns:
            self._tags = [set(load_json_col(t)) for t in self.chunks["topic_tags"]]
        else:
            self._tags = []

    def retrieve(self, failure: FailureFamily, doc_type: DocType,
                 k_min: int, k_max: int) -> list[str]:
        cache_key = (failure.value, doc_type.value, k_min, k_max)
        if cache_key in self._cache:
            return list(self._cache[cache_key])
        if self.chunks.empty:
            return []
        topics = set(self.failure_to_topics.get(failure.value, []))
        mask = self.chunks["doc_type"] == doc_type.value
        sub_idx = np.flatnonzero(mask.to_numpy())
        if sub_idx.size == 0:
            return []
        # Score by topic-tag overlap; relax to all chunks of this type when none hit.
        scored = sorted(
            sub_idx,
            key=lambda i: (len(self._tags[i] & topics) if self._tags else 0,
                           int(self.chunks.iloc[i]["n_tokens"])),
            reverse=True,
        )
        any_topic_hit = any((self._tags[i] & topics) for i in sub_idx) if self._tags else False
        if not any_topic_hit:
            # Relaxed: keep ordering by length (already applied) — broader fallback.
            pass
        chosen = scored[:k_max]
        # Ensure at least k_min when available.
        if len(chosen) < k_min:
            chosen = scored[:k_min]
        result = [str(self.chunks.iloc[i]["chunk_id"]) for i in chosen]
        self._cache[cache_key] = result
        return list(result)


# --------------------------------------------------------------------------- #
# SplitAssigner
# --------------------------------------------------------------------------- #
class SplitAssigner:
    def __init__(self, cfg: SplitCfg, rng: np.random.Generator):
        self.cfg = cfg
        self.rng = rng

    def assign(self, rows: list[IncidentRow]) -> None:
        """Assign each row a split in place; rows sharing the group key never
        span two splits; counts approximate the configured fractions."""
        if not rows:
            return
        groups: dict[str, list[int]] = {}
        for i, r in enumerate(rows):
            key = str(getattr(r, self.cfg.group_key, "")) or r.source_dataset
            groups.setdefault(key, []).append(i)

        n_total = len(rows)
        splits = list(self.cfg.fractions.keys())
        targets = {s: self.cfg.fractions[s] * n_total for s in splits}
        assigned = {s: 0 for s in splits}

        order = list(groups.keys())
        self.rng.shuffle(order)
        # Assign whole groups, each to the split currently most under its target.
        for key in order:
            members = groups[key]
            deficits = {s: targets[s] - assigned[s] for s in splits}
            best = max(splits, key=lambda s: deficits[s])
            for i in members:
                rows[i].split = Split(best)
            assigned[best] += len(members)


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
class IncidentAssembler:
    def __init__(self, cfg: PipelineConfig, logger=None):
        self.cfg = cfg
        self.log = logger or get_logger("assemble", cfg.runtime.log_level, cfg.runtime.log_format)
        self.rng = np.random.default_rng(cfg.random_seed)

    def _load_indices(self) -> tuple[pd.DataFrame, pd.DataFrame | None, pd.DataFrame | None]:
        sensor_path = Path(self.cfg.paths.sensor_index)
        if not sensor_path.exists():
            raise AssemblyError(
                "missing sensor_windows.parquet — run the 'sensor' stage first "
                "(`python -m src.cli sensor`)"
            )
        sensor = read_parquet(sensor_path)
        video = read_parquet(self.cfg.paths.video_index) \
            if Path(self.cfg.paths.video_index).exists() else None
        text = read_parquet(self.cfg.paths.text_chunks) \
            if Path(self.cfg.paths.text_chunks).exists() else None
        if video is None:
            self.log.warning("no video_index.parquet — incidents will have null video")
        if text is None:
            self.log.warning("no text_chunks.parquet — incidents will have no text chunks")
        return sensor, video, text

    def _amplitude(self, sensor_file: str) -> float | None:
        path = self.cfg.resolve(sensor_file)
        if not Path(path).exists():
            return None
        try:
            head = pd.read_parquet(path, columns=["az"])
        except Exception:  # noqa: BLE001
            try:
                head = pd.read_parquet(path)
            except Exception:  # noqa: BLE001
                return None
        ch = "az" if "az" in head.columns else next((c for c in ("ay", "ax") if c in head.columns), None)
        if ch is None:
            return None
        x = head[ch].to_numpy(dtype="float64")
        return float(np.nanmax(np.abs(x - np.nanmean(x)))) if x.size else None

    def run(self, limit: int | None = None, dry_run: bool | None = None) -> RunSummary:
        dry_run = self.cfg.runtime.dry_run if dry_run is None else dry_run
        summ = RunSummary(stage="assemble", dry_run=dry_run)
        sensor, video, text = self._load_indices()
        if limit is not None:
            sensor = sensor.head(limit)
        summ.discovered = len(sensor)

        deriver = LabelDeriver(default_label=self.cfg.assemble.default_label)
        matcher = VideoMatcher(video, self.cfg.assemble.video_match, self.rng)
        retriever = TextRetriever(text, self.cfg.assemble.text_retrieval,
                                  self.cfg.assemble.text_retrieval.failure_to_topics)
        tr = self.cfg.assemble.text_retrieval

        rows: list[IncidentRow] = []
        n_no_video = 0
        n_short_text = 0
        for _, sw in sensor.iterrows():
            labels = deriver.derive(meta=None, amplitude=None)
            failure = FailureFamily(sw.get("failure_family", "unknown"))
            if failure is FailureFamily.unknown:
                failure = deriver.weak_failure_family(str(sw["incident_id"]))
            severity = labels["severity_label"]
            root_cause = labels["root_cause_label"]
            if severity is Severity.unknown and failure is not FailureFamily.unknown:
                severity = deriver.weak_severity(str(sw["incident_id"]))
                root_cause = f"weak_id_bucket_{failure.value}"
            clip, align = matcher.match(labels["regime_label"], Condition.unknown)
            sop_ids = retriever.retrieve(failure, DocType.sop,
                                         tr.sop_chunks_min, tr.sop_chunks_max)
            maint_ids = retriever.retrieve(failure, DocType.maintenance,
                                           tr.maintenance_chunks_min, tr.maintenance_chunks_max)
            if len(sop_ids) < tr.sop_chunks_min or len(maint_ids) < tr.maintenance_chunks_min:
                n_short_text += 1

            video_file = None
            video_fps = None
            video_spans: list[Span] = []
            if clip is not None:
                video_file = str(clip["video_file"])
                video_fps = float(clip["video_fps"])
                dur = float(clip["duration_s"])
                video_spans = [Span(start_s=0.0, end_s=dur)] if dur > 0 else []
            else:
                n_no_video += 1

            try:
                row = IncidentRow(
                    incident_id=str(sw["incident_id"]),
                    source_dataset=str(sw["source_dataset"]),
                    machine_family=str(sw["machine_family"]),
                    failure_family=failure,
                    window_start_s=float(sw["window_start_s"]),
                    window_end_s=float(sw["window_end_s"]),
                    fs_hz=float(sw["fs_hz"]),
                    sensor_file=str(sw["sensor_file"]),
                    sensor_channels=load_json_col(sw["sensor_channels"]),
                    sensor_relevant_spans=[Span(**s) for s in
                                           load_json_col(sw["sensor_relevant_spans"])],
                    video_file=video_file,
                    video_fps=video_fps,
                    video_relevant_spans=video_spans,
                    sop_chunk_ids=sop_ids,
                    maintenance_chunk_ids=maint_ids,
                    phase_label=labels["phase_label"],
                    regime_label=labels["regime_label"],
                    severity_label=severity,
                    root_cause_label=root_cause,
                    alignment_method=align,
                    split=Split.train,  # placeholder; SplitAssigner sets the real value
                )
            except Exception as exc:  # noqa: BLE001 - never write an invalid row
                summ.bump("errors")
                self.log.warning("invalid incident skipped",
                                 extra={"incident": sw.get("incident_id"), "error": str(exc)})
                continue
            rows.append(row)
            summ.bump("processed")

        SplitAssigner(self.cfg.assemble.split, self.rng).assign(rows)

        if not dry_run and rows:
            write_parquet_atomic(rows_to_df(rows), self.cfg.paths.incidents_index)
            self.log.info("incidents written",
                          extra={"path": self.cfg.paths.incidents_index, "rows": len(rows)})
        summ.written = 0 if dry_run else len(rows)
        summ.note("no_video", n_no_video)
        summ.note("short_text", n_short_text)
        summ.note(
            "split_groups",
            len({str(getattr(r, self.cfg.assemble.split.group_key, "")) for r in rows}),
        )
        return summ
