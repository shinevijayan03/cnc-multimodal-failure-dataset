"""Pure logic for the incident workbench UI (temporal alignment refactor).

Everything here is Streamlit-free and unit-testable: shared playback state,
timeline event construction, grounded explanation/claim rows, and the evidence
report export. Rendering lives in ``streamlit_app.py``.

Data provenance rule (UI refactor spec R2/rule 8-10): every event carries a
``source`` field —
  * ``incident``  — read directly from incident data (e.g. sensor evidence spans)
  * ``derived``   — computed from incident data (e.g. baseline = span complement)
  * ``demo``      — illustrative placeholder; no real timing/label data exists yet
Demo events are labeled as such in the UI and in exports.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from src.common.io_utils import load_json_col

TIMELINE_ROWS = ("SENSOR", "VIDEO", "SOP", "AI CLAIMS", "NOTES")

ROW_COLORS = {
    "SENSOR": "#38bdf8",     # sky
    "VIDEO": "#a78bfa",      # violet
    "SOP": "#34d399",        # emerald
    "AI CLAIMS": "#f59e0b",  # amber
    "NOTES": "#f472b6",      # pink
}

SOURCE_BADGE = {"incident": "", "derived": " · derived", "demo": " · demo"}


# --------------------------------------------------------------------------- #
# Shared playback state (R3)
# --------------------------------------------------------------------------- #
@dataclass
class PlaybackState:
    """One shared clock for video, sensor chart, timeline, and evidence panes."""

    t0: float = 0.0                    # incident-relative axis start
    t1: float = 0.0                    # incident-relative axis end
    current_time_s: float = 0.0
    is_playing: bool = False
    playback_rate: float = 1.0
    selected_event_id: str | None = None

    @property
    def duration_s(self) -> float:
        return max(0.0, self.t1 - self.t0)

    def play(self) -> None:
        if self.current_time_s >= self.t1:      # play-through restarts from t0
            self.current_time_s = self.t0
        self.is_playing = True

    def stop(self) -> None:
        self.is_playing = False

    def seek(self, t: float) -> None:
        self.current_time_s = min(max(float(t), self.t0), self.t1)

    def tick(self, dt_s: float) -> None:
        """Advance the clock by wall-clock *dt_s*; auto-stop at the end."""
        if not self.is_playing or dt_s <= 0:
            return
        self.current_time_s += dt_s * self.playback_rate
        if self.current_time_s >= self.t1:
            self.current_time_s = self.t1
            self.is_playing = False


def video_offset_for(state: PlaybackState, clip_duration_s: float) -> float:
    """Map the incident-relative cursor onto a clip-relative playback offset.

    The linked clip is label-matched, not time-synchronized (sync_provenance is
    'constructed'), so the mapping is proportional: incident progress fraction
    -> clip offset. Honest best-effort alignment, documented in the UI.
    """
    if state.duration_s <= 0 or clip_duration_s <= 0:
        return 0.0
    frac = (state.current_time_s - state.t0) / state.duration_s
    return min(max(frac, 0.0), 1.0) * clip_duration_s


# --------------------------------------------------------------------------- #
# Timeline events (R2)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class TimelineEvent:
    event_id: str
    row: str                  # one of TIMELINE_ROWS
    label: str
    t_start: float
    t_end: float
    source: str               # incident | derived | demo
    detail: str = ""

    def contains(self, t: float) -> bool:
        return self.t_start <= t <= self.t_end


def _spans_from_incident(incident: pd.Series, column: str) -> list[tuple[float, float]]:
    spans = []
    for span in load_json_col(incident.get(column)):
        if isinstance(span, dict) and "start_s" in span and "end_s" in span:
            spans.append((float(span["start_s"]), float(span["end_s"])))
    return spans


def _clip(lo: float, hi: float, t0: float, t1: float) -> tuple[float, float]:
    return max(lo, t0), min(hi, t1)


def sensor_events(incident: pd.Series, t0: float, t1: float) -> list[TimelineEvent]:
    """Real evidence spans + derived baseline complement."""
    events: list[TimelineEvent] = []
    spans = sorted(_spans_from_incident(incident, "sensor_relevant_spans"))
    idx = 0
    for lo, hi in spans:
        lo, hi = _clip(lo, hi, t0, t1)
        if hi <= lo:
            continue
        events.append(TimelineEvent(
            event_id=f"ev_sensor_{idx:02d}", row="SENSOR",
            label="Vibration anomaly (evidence span)",
            t_start=lo, t_end=hi, source="incident",
            detail="sensor_relevant_spans from incidents.parquet"))
        idx += 1
    # Baseline = complement of the evidence spans over the axis.
    cursor = t0
    for lo, hi in [(e.t_start, e.t_end) for e in events] + [(t1, t1)]:
        if lo - cursor > 0.5:
            events.append(TimelineEvent(
                event_id=f"ev_sensor_{idx:02d}", row="SENSOR",
                label="Baseline / normal",
                t_start=cursor, t_end=lo, source="derived",
                detail="complement of evidence spans"))
            idx += 1
        cursor = max(cursor, hi)
    return sorted(events, key=lambda e: e.t_start)


_DEMO_VIDEO_PATTERN = (
    (0.00, 0.55, "Normal operation"),
    (0.55, 0.70, "Subtle shaft wobble"),
    (0.70, 0.85, "Oscillatory shaft motion"),
    (0.85, 1.00, "Surface heat signature"),
)


def video_events(incident: pd.Series, t0: float, t1: float) -> list[TimelineEvent]:
    """Real video spans when present; otherwise a clearly-marked demo pattern."""
    spans = _spans_from_incident(incident, "video_relevant_spans")
    if spans:
        return [TimelineEvent(
            event_id=f"ev_video_{i:02d}", row="VIDEO", label="Video evidence span",
            t_start=max(lo, t0), t_end=min(hi, t1), source="incident",
            detail="video_relevant_spans from incidents.parquet")
            for i, (lo, hi) in enumerate(sorted(spans))]
    dur = t1 - t0
    return [TimelineEvent(
        event_id=f"ev_video_{i:02d}", row="VIDEO", label=label,
        t_start=t0 + f_lo * dur, t_end=t0 + f_hi * dur, source="demo",
        detail="demo pattern — no VLM video events until Build Phase 7")
        for i, (f_lo, f_hi, label) in enumerate(_DEMO_VIDEO_PATTERN)]


def sop_events(incident: pd.Series, t0: float, t1: float) -> list[TimelineEvent]:
    """Real chunk IDs; timing is demo (chunks carry no time data until Phase 8)."""
    sop_ids = [str(x) for x in load_json_col(incident.get("sop_chunk_ids"))][:3]
    maint_ids = [str(x) for x in load_json_col(incident.get("maintenance_chunk_ids"))][:2]
    dur = t1 - t0
    slots = ((0.50, 0.80), (0.55, 0.75), (0.70, 0.90), (0.60, 0.85), (0.75, 0.95))
    events = []
    for i, (kind, chunk_id) in enumerate(
            [("SOP", c) for c in sop_ids] + [("Manual", c) for c in maint_ids]):
        f_lo, f_hi = slots[i % len(slots)]
        events.append(TimelineEvent(
            event_id=f"ev_sop_{i:02d}", row="SOP",
            label=f"{kind} {chunk_id} matched",
            t_start=t0 + f_lo * dur, t_end=t0 + f_hi * dur, source="demo",
            detail="chunk id is real (incidents.parquet); time placement is demo"))
    return events


def claim_events(incident: pd.Series, t0: float, t1: float,
                 sensor: list[TimelineEvent]) -> list[TimelineEvent]:
    """Demo claims; claim 1 is anchored to the real sensor evidence span."""
    anchor = next((e for e in sensor if e.source == "incident"), None)
    dur = t1 - t0
    events = []
    if anchor is not None:
        events.append(TimelineEvent(
            event_id="ev_claim_00", row="AI CLAIMS",
            label="Claim 1: vibration RMS rose (anchored to evidence span)",
            t_start=anchor.t_start, t_end=anchor.t_end, source="demo",
            detail="span from real sensor evidence; claim text is demo until Phase 11"))
    events.append(TimelineEvent(
        event_id="ev_claim_01", row="AI CLAIMS",
        label="Claim 2: anomaly aligned with video motion",
        t_start=t0 + 0.60 * dur, t_end=t0 + 0.80 * dur, source="demo",
        detail="demo — decoder LLM lands in Build Phase 11"))
    events.append(TimelineEvent(
        event_id="ev_claim_02", row="AI CLAIMS",
        label="Claim 3: SOP links symptom to bearing/tool wear",
        t_start=t0 + 0.70 * dur, t_end=t0 + 0.92 * dur, source="demo",
        detail="demo — decoder LLM lands in Build Phase 11"))
    return events


def note_events(t0: float, t1: float) -> list[TimelineEvent]:
    dur = t1 - t0
    return [TimelineEvent(
        event_id="ev_note_00", row="NOTES", label="Engineer flag",
        t_start=t0 + 0.62 * dur, t_end=t0 + 0.78 * dur, source="demo",
        detail="demo — user annotations are a later feature")]


def build_timeline_events(incident: pd.Series, t0: float, t1: float) -> list[TimelineEvent]:
    """All timeline rows for one incident, incident-relative time axis."""
    sensor = sensor_events(incident, t0, t1)
    return (sensor
            + video_events(incident, t0, t1)
            + sop_events(incident, t0, t1)
            + claim_events(incident, t0, t1, sensor)
            + note_events(t0, t1))


def events_frame(events: list[TimelineEvent], current_time_s: float) -> pd.DataFrame:
    """Long-form frame for the Gantt-style timeline chart."""
    rows = []
    for e in events:
        rows.append({
            **asdict(e),
            "display_label": e.label + SOURCE_BADGE.get(e.source, ""),
            "active": e.contains(current_time_s),
            "color": ROW_COLORS.get(e.row, "#94a3b8"),
        })
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["row"] = pd.Categorical(frame["row"], categories=list(TIMELINE_ROWS),
                                      ordered=True)
    return frame


def active_events(events: list[TimelineEvent], t: float) -> list[TimelineEvent]:
    return [e for e in events if e.contains(t)]


# --------------------------------------------------------------------------- #
# Evidence panel content (R6)
# --------------------------------------------------------------------------- #
def build_ai_explanation(incident: pd.Series, events: list[TimelineEvent]) -> list[dict]:
    """Grounded explanation sentences; every sentence lists its provenance."""
    spans = [e for e in events if e.row == "SENSOR" and e.source == "incident"]
    sop = [e for e in events if e.row == "SOP"]
    sentences: list[dict] = []
    if spans:
        first = spans[0]
        sentences.append({
            "text": (f"Vibration RMS evidence span from t={first.t_start:.1f}s to "
                     f"t={first.t_end:.1f}s marks the anomalous interval in the sensor data."),
            "evidence": [first.event_id],
            "source": "incident",
        })
    sentences.append({
        "text": ("Video shows motion consistent with the sensor anomaly interval "
                 "(label-matched clip; not time-synchronized ground truth)."),
        "evidence": [e.event_id for e in events if e.row == "VIDEO"][:2],
        "source": "demo",
    })
    if sop:
        ids = ", ".join(e.label.split(" matched")[0] for e in sop[:2])
        sentences.append({
            "text": f"Retrieved documentation ({ids}) supports the "
                    f"{incident.get('failure_family', 'unknown')} diagnosis.",
            "evidence": [e.event_id for e in sop[:2]],
            "source": "demo",
        })
    sentences.append({
        "text": "Full grounded explanation generation lands in Build Phase 11 "
                "(decoder LLM with GBNF-constrained output).",
        "evidence": [],
        "source": "demo",
    })
    return sentences


def build_claim_rows(events: list[TimelineEvent]) -> list[dict]:
    """Claim-verification table rows derived from the AI CLAIMS timeline row."""
    rows = []
    for e in [ev for ev in events if ev.row == "AI CLAIMS"]:
        anchored = "anchored to evidence span" in e.label or "real sensor" in e.detail
        rows.append({
            "claim_id": e.event_id,
            "claim": e.label,
            "span": f"{e.t_start:.1f}s – {e.t_end:.1f}s",
            "status": "SUPPORTED (span verified)" if anchored else "UNVERIFIED (demo)",
            "source": e.source,
        })
    return rows


# --------------------------------------------------------------------------- #
# Export evidence report (R7)
# --------------------------------------------------------------------------- #
def export_report(incident: pd.Series, events: list[TimelineEvent],
                  explanation: list[dict], claims: list[dict],
                  state: PlaybackState) -> dict[str, Any]:
    return {
        "report_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "incident": {
            "incident_id": str(incident.get("incident_id", "")),
            "equipment": str(incident.get("machine_family", "unknown")),
            "source_dataset": str(incident.get("source_dataset", "unknown")),
            "failure_family": str(incident.get("failure_family", "unknown")),
            "severity": str(incident.get("severity_label", "unknown")),
            "split": str(incident.get("split", "unknown")),
            "window_start_s": float(incident.get("window_start_s", 0.0)),
            "window_end_s": float(incident.get("window_end_s", 0.0)),
            "sensor_file": str(incident.get("sensor_file", "")),
            "video_file": str(incident.get("video_file", "") or ""),
        },
        "time_axis": {"t0": state.t0, "t1": state.t1,
                      "cursor_at_export": round(state.current_time_s, 3)},
        "timeline_events": [asdict(e) for e in events],
        "ai_explanation": explanation,
        "claim_verification": claims,
        "provenance_note": (
            "Events marked source='demo' are illustrative placeholders; "
            "source='incident' fields come from incidents.parquet; "
            "video alignment is constructed (label-matched), not measured."
        ),
    }


def export_report_json(incident: pd.Series, events: list[TimelineEvent],
                       explanation: list[dict], claims: list[dict],
                       state: PlaybackState) -> str:
    return json.dumps(export_report(incident, events, explanation, claims, state),
                      indent=2, sort_keys=True)
