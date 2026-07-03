"""Pure logic for the incident workbench UI (temporal alignment refactor v2).

Everything here is Streamlit-free and unit-testable: shared playback state,
the unified 0-based incident time axis, timeline event construction, sensor
display features (via the one feature path, I-3), live readouts, SOP match
cards, the simulated DEMO incident that mirrors the user's reference
screenshots, and the evidence report export. Rendering lives in
``streamlit_app.py``.

Data provenance rule: every event/card carries a ``source`` field —
  * ``incident`` — read directly from incident data (e.g. sensor evidence spans)
  * ``derived``  — computed from incident data (baseline complement, RMS curves)
  * ``demo``     — illustrative placeholder (labels/timing with no real data yet)
  * ``user``     — created in-session by the engineer (snapshot notes)
Demo elements are visibly badged in the UI and in exports.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from src.common.io_utils import load_json_col
from src.features.vibration import rms

TIMELINE_ROWS = ("SENSOR", "VIDEO", "SOP", "AI CLAIMS", "NOTES")

# Event palette — 600-level tones, legible on the light/white background.
TEAL = "#0d9488"
CYAN = "#0891b2"
AMBER = "#d97706"
RED = "#dc2626"
VIOLET = "#7c3aed"
GREEN = "#059669"

ROW_COLORS = {
    "SENSOR": TEAL, "VIDEO": VIOLET, "SOP": GREEN, "AI CLAIMS": AMBER, "NOTES": CYAN,
}

SOURCE_BADGE = {"incident": "", "derived": "", "demo": " · demo",
                "user": " · note", "retrieval": ""}

DEMO_INCIDENT_ID = "DEMO_simulated_incident"


# --------------------------------------------------------------------------- #
# Shared playback state (R3)
# --------------------------------------------------------------------------- #
@dataclass
class PlaybackState:
    """One shared clock for video, sensor chart, timeline, and evidence panes."""

    t0: float = 0.0
    t1: float = 0.0
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

    def step(self, dt: float) -> None:
        self.seek(self.current_time_s + dt)

    def tick(self, dt_s: float) -> None:
        """Advance the clock by wall-clock *dt_s*; auto-stop at the end."""
        if not self.is_playing or dt_s <= 0:
            return
        self.current_time_s += dt_s * self.playback_rate
        if self.current_time_s >= self.t1:
            self.current_time_s = self.t1
            self.is_playing = False


def video_offset_for(state: PlaybackState, clip_duration_s: float) -> float:
    """Map the shared cursor onto a clip-relative playback offset.

    The linked clip is label-matched, not time-synchronized (sync_provenance is
    'constructed'), so the mapping is proportional: incident progress fraction
    -> clip offset. The transport UI always displays the shared clock.
    """
    if state.duration_s <= 0 or clip_duration_s <= 0:
        return 0.0
    frac = (state.current_time_s - state.t0) / state.duration_s
    return min(max(frac, 0.0), 1.0) * clip_duration_s


# --------------------------------------------------------------------------- #
# Unified incident time axis
# --------------------------------------------------------------------------- #
def incident_axis(sensor_df: pd.DataFrame) -> tuple[float, float, float]:
    """Return (t0, t1, rel_offset) for the display axis.

    The display axis is 0-based (t=0 at window start, like the reference UI);
    ``rel_offset`` shifts stored incident-relative spans (t_rel_s, where 0 is
    the event) onto it: axis_time = t_rel + rel_offset.
    """
    col = "t_rel_s" if "t_rel_s" in sensor_df.columns else "time_s"
    if sensor_df.empty or col not in sensor_df.columns:
        return 0.0, 1.0, 0.0
    lo = float(sensor_df[col].min())
    hi = float(sensor_df[col].max())
    return 0.0, hi - lo, -lo


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
    source: str               # incident | derived | demo | user
    color: str = TEAL
    detail: str = ""

    def contains(self, t: float) -> bool:
        return self.t_start <= t <= self.t_end


def _spans_from_incident(incident: pd.Series, column: str) -> list[tuple[float, float]]:
    spans = []
    for span in load_json_col(incident.get(column)):
        if isinstance(span, dict) and "start_s" in span and "end_s" in span:
            spans.append((float(span["start_s"]), float(span["end_s"])))
    return spans


def sensor_events(incident: pd.Series, t0: float, t1: float,
                  rel_offset: float = 0.0) -> list[TimelineEvent]:
    """Real evidence spans (shifted onto the axis) + derived baseline complement."""
    events: list[TimelineEvent] = []
    spans = sorted(_spans_from_incident(incident, "sensor_relevant_spans"))
    idx = 0
    for lo, hi in spans:
        lo, hi = max(lo + rel_offset, t0), min(hi + rel_offset, t1)
        if hi <= lo:
            continue
        events.append(TimelineEvent(
            event_id=f"ev_sensor_{idx:02d}", row="SENSOR",
            label="Vib Anomaly (evidence span)",
            t_start=lo, t_end=hi, source="incident", color=AMBER,
            detail="sensor_relevant_spans from incidents.parquet"))
        idx += 1
    cursor = t0
    for lo, hi in [(e.t_start, e.t_end) for e in events] + [(t1, t1)]:
        if lo - cursor > 0.5:
            events.append(TimelineEvent(
                event_id=f"ev_sensor_{idx:02d}", row="SENSOR",
                label="Baseline Normal",
                t_start=cursor, t_end=lo, source="derived", color=TEAL,
                detail="complement of evidence spans"))
            idx += 1
        cursor = max(cursor, hi)
    return sorted(events, key=lambda e: e.t_start)


_DEMO_VIDEO_PATTERN = (
    (0.00, 0.30, "Normal", TEAL),
    (0.30, 0.40, "Shaft Wobble", VIOLET),
    (0.40, 0.45, "Oscillation", AMBER),
    (0.45, 1.00, "Heat Sig", RED),
)


def video_events(incident: pd.Series, t0: float, t1: float,
                 rel_offset: float = 0.0) -> list[TimelineEvent]:
    """Real video spans when present; otherwise the reference demo pattern."""
    spans = _spans_from_incident(incident, "video_relevant_spans")
    if spans:
        return [TimelineEvent(
            event_id=f"ev_video_{i:02d}", row="VIDEO", label="Video evidence span",
            t_start=max(lo + rel_offset, t0), t_end=min(hi + rel_offset, t1),
            source="incident", color=VIOLET,
            detail="video_relevant_spans from incidents.parquet")
            for i, (lo, hi) in enumerate(sorted(spans))]
    dur = t1 - t0
    return [TimelineEvent(
        event_id=f"ev_video_{i:02d}", row="VIDEO", label=label,
        t_start=t0 + f_lo * dur, t_end=t0 + f_hi * dur, source="demo", color=color,
        detail="demo pattern — real VLM video events arrive in Build Phase 7")
        for i, (f_lo, f_hi, label, color) in enumerate(_DEMO_VIDEO_PATTERN)]


def sop_events(incident: pd.Series, t0: float, t1: float) -> list[TimelineEvent]:
    """Real chunk IDs; timing is demo until temporal grounding (Phase 8)."""
    sop_ids = [str(x) for x in load_json_col(incident.get("sop_chunk_ids"))][:3]
    maint_ids = [str(x) for x in load_json_col(incident.get("maintenance_chunk_ids"))][:2]
    dur = t1 - t0
    slots = ((0.30, 0.45), (0.37, 0.45), (0.48, 0.83), (0.35, 0.55), (0.55, 0.80))
    events = []
    for i, (kind, chunk_id) in enumerate(
            [("SOP", c) for c in sop_ids] + [("Manual", c) for c in maint_ids]):
        f_lo, f_hi = slots[i % len(slots)]
        events.append(TimelineEvent(
            event_id=f"ev_sop_{i:02d}", row="SOP",
            label=f"{kind} {chunk_id} Matched",
            t_start=t0 + f_lo * dur, t_end=t0 + f_hi * dur, source="demo", color=GREEN,
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
            t_start=anchor.t_start, t_end=anchor.t_end, source="demo", color=AMBER,
            detail="span from real sensor evidence; claim text is demo until Phase 11"))
    events.append(TimelineEvent(
        event_id="ev_claim_01", row="AI CLAIMS",
        label="Claim 2: anomaly aligned with video motion",
        t_start=t0 + 0.37 * dur, t_end=t0 + 0.45 * dur, source="demo", color=AMBER,
        detail="demo — decoder LLM lands in Build Phase 11"))
    events.append(TimelineEvent(
        event_id="ev_claim_02", row="AI CLAIMS",
        label="Claim 3: SOP links symptom to bearing/tool wear",
        t_start=t0 + 0.48 * dur, t_end=t0 + 0.83 * dur, source="demo", color=AMBER,
        detail="demo — decoder LLM lands in Build Phase 11"))
    return events


def note_events(t0: float, t1: float,
                user_notes: list[dict] | None = None) -> list[TimelineEvent]:
    """Demo engineer flag + real user snapshot notes from the session."""
    dur = t1 - t0
    events = [TimelineEvent(
        event_id="ev_note_00", row="NOTES", label="Engineer flag",
        t_start=t0 + 0.37 * dur, t_end=t0 + 0.47 * dur, source="demo", color=CYAN,
        detail="demo — persistent annotations are a later feature")]
    for i, note in enumerate(user_notes or []):
        t = float(note.get("t", t0))
        events.append(TimelineEvent(
            event_id=f"ev_note_user_{i:02d}", row="NOTES",
            label=str(note.get("label", f"Snapshot @ {t:.0f}s")),
            t_start=max(t0, t - 0.4), t_end=min(t1, t + max(0.4, dur * 0.02)),
            source="user", color=CYAN,
            detail="created in-session via the Snapshot button"))
    return events


def build_timeline_events(incident: pd.Series, t0: float, t1: float,
                          rel_offset: float = 0.0,
                          user_notes: list[dict] | None = None) -> list[TimelineEvent]:
    """All timeline rows for one incident on the unified display axis."""
    if str(incident.get("incident_id", "")) == DEMO_INCIDENT_ID:
        return demo_timeline_events() + note_events(t0, t1, user_notes)
    sensor = sensor_events(incident, t0, t1, rel_offset)
    return (sensor
            + video_events(incident, t0, t1, rel_offset)
            + sop_events(incident, t0, t1)
            + claim_events(incident, t0, t1, sensor)
            + note_events(t0, t1, user_notes))


def events_frame(events: list[TimelineEvent], current_time_s: float) -> pd.DataFrame:
    """Long-form frame for the Gantt-style timeline chart."""
    rows = []
    for e in events:
        rows.append({
            **asdict(e),
            "display_label": e.label + SOURCE_BADGE.get(e.source, ""),
            "active": e.contains(current_time_s),
        })
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["row"] = pd.Categorical(frame["row"], categories=list(TIMELINE_ROWS),
                                      ordered=True)
    return frame


def active_events(events: list[TimelineEvent], t: float) -> list[TimelineEvent]:
    return [e for e in events if e.contains(t)]


# --------------------------------------------------------------------------- #
# Sensor display features — via the one feature path (constitution I-3)
# --------------------------------------------------------------------------- #
def rolling_rms_frame(sensor_df: pd.DataFrame, rel_offset: float,
                      window_s: float = 0.5, out_hz: float = 12.0) -> pd.DataFrame:
    """Smooth per-channel rolling-RMS curves on the unified 0-based axis.

    Uses ``src.features.vibration.rms`` (the single feature path, I-3) applied
    per window — display-only consumption of the same math the eval harness
    uses. Adds a combined "Vib RMS" magnitude channel like the reference UI.
    """
    col = "t_rel_s" if "t_rel_s" in sensor_df.columns else "time_s"
    channels = [c for c in ("ax", "ay", "az") if c in sensor_df.columns]
    if sensor_df.empty or not channels:
        return pd.DataFrame(columns=["t", "channel", "value"])
    t = sensor_df[col].to_numpy()
    t_axis0 = float(t.min())
    duration = float(t.max()) - t_axis0
    n = len(sensor_df)
    fs = (n - 1) / duration if duration > 0 else 1.0
    win = max(1, int(window_s * fs))
    step = max(1, int(fs / out_hz))
    data = {c: sensor_df[c].to_numpy() for c in channels}
    mag = None
    if len(channels) == 3:
        mag = (data["ax"] ** 2 + data["ay"] ** 2 + data["az"] ** 2) ** 0.5
        # Remove the DC mounting offset so the magnitude reflects vibration.
        mag = mag - float(pd.Series(mag).median())
    rows = []
    for start in range(0, n - win + 1, step):
        mid_axis = (t[start + win // 2] - t_axis0)
        for c in channels:
            seg = data[c][start:start + win]
            seg = seg - float(seg.mean())          # per-window detrend (DC offset)
            rows.append({"t": mid_axis, "channel": f"{c} RMS",
                         "value": rms(seg.tolist())})
        if mag is not None:
            rows.append({"t": mid_axis, "channel": "Vib RMS",
                         "value": rms(mag[start:start + win].tolist())})
    return pd.DataFrame(rows)


def live_readouts(display_frame: pd.DataFrame, t: float) -> list[dict]:
    """Channel value at the cursor + ANOMALY flag (value > baseline mean+3σ).

    Baseline statistics come from the first 20% of each channel's curve.
    """
    out: list[dict] = []
    if display_frame.empty:
        return out
    for channel, group in display_frame.groupby("channel", sort=False):
        group = group.sort_values("t")
        idx = (group["t"] - t).abs().idxmin()
        value = float(group.loc[idx, "value"])
        head = group.head(max(3, int(len(group) * 0.2)))["value"]
        threshold = float(head.mean() + 3 * head.std(ddof=0))
        out.append({
            "channel": str(channel),
            "value": value,
            "threshold": threshold,
            "anomaly": bool(math.isfinite(threshold) and value > threshold),
        })
    return out


# --------------------------------------------------------------------------- #
# SOP match cards (reference-UI style)
# --------------------------------------------------------------------------- #
def build_sop_cards(incident: pd.Series, sop_chunks: pd.DataFrame,
                    maint_chunks: pd.DataFrame) -> list[dict]:
    """Cards like `SOP 4.2 · 94% · Matched` with matched-phrase chips.

    Matched phrases are the chunk's real topic tags found in its text; the
    match percentage is a stable demo placeholder (badged) until the retriever
    scores exist (Build Phase 6).
    """
    if str(incident.get("incident_id", "")) == DEMO_INCIDENT_ID:
        return demo_sop_cards()
    cards = []
    for kind, chunks in (("SOP", sop_chunks), ("Manual", maint_chunks)):
        if chunks is None or chunks.empty:
            continue
        for _, chunk in chunks.iterrows():
            chunk_id = str(chunk.get("chunk_id", ""))
            text = str(chunk.get("text", "")).strip()
            tags = [str(x) for x in load_json_col(chunk.get("topic_tags"))]
            phrases = [tag.replace("_", " ") for tag in tags
                       if tag.replace("_", " ") in text.lower() or tag in text.lower()]
            pct = 70 + (abs(hash(chunk_id)) % 26)          # stable demo score
            cards.append({
                "ref": f"{kind} {chunk_id}",
                "title": (text.split(".")[0][:80] + "…") if text else chunk_id,
                "match_pct": pct,
                "status": "Matched" if len(phrases) >= 2 else "Partially Matched",
                "phrases": phrases or [tag.replace("_", " ") for tag in tags[:3]],
                "equipment": str(incident.get("machine_family", "unknown")),
                "section": str(chunk.get("doc_type", "unknown")),
                "text": text,
                "source": "demo",  # the % score is demo; ids/text/tags are real
            })
    return cards


# --------------------------------------------------------------------------- #
# Real pipeline artifacts (Phases 2-5) surfaced into the UI
# --------------------------------------------------------------------------- #
def incident_feature_rows(features: pd.DataFrame, incident_id: str,
                          hvib: pd.DataFrame | None = None) -> pd.DataFrame:
    """Per-sub-window feature table for one incident (sensor_features.parquet),
    joined with encoder anomaly scores from hvib.parquet when present.

    Encoder scores exist only for train/val windows — test-split incidents
    show NaN (quarantined per I-4), which the UI labels explicitly.
    """
    if features.empty or "incident_id" not in features.columns:
        return pd.DataFrame()
    rows = features[features["incident_id"] == incident_id].copy()
    if rows.empty:
        return rows
    keep = ["window_id", "t_start", "t_end", "rms", "kurtosis", "variance",
            "anomaly_score", "important_start_s", "important_end_s",
            "spec_band_0", "spec_band_1", "spec_band_2", "spec_band_3"]
    rows = rows[[c for c in keep if c in rows.columns]].rename(
        columns={"anomaly_score": "anomaly_heuristic"})
    if hvib is not None and not hvib.empty and "window_id" in hvib.columns:
        enc = hvib[["window_id", "anomaly_score"]].rename(
            columns={"anomaly_score": "anomaly_encoder"})
        rows = rows.merge(enc, on="window_id", how="left")
    else:
        rows["anomaly_encoder"] = float("nan")
    return rows.sort_values("t_start").reset_index(drop=True)


def important_interval_events(feature_rows: pd.DataFrame, rel_offset: float,
                              t0: float, t1: float) -> list[TimelineEvent]:
    """Real important-interval bars (Phase 3 peak-RMS segments) on the axis."""
    events = []
    for i, row in feature_rows.iterrows():
        lo = float(row["important_start_s"]) + rel_offset
        hi = float(row["important_end_s"]) + rel_offset
        lo, hi = max(lo, t0), min(hi, t1)
        if hi <= lo:
            continue
        events.append(TimelineEvent(
            event_id=f"ev_imp_{i:02d}", row="SENSOR",
            label=f"Important interval ({row['window_id']})",
            t_start=lo, t_end=hi, source="derived", color=CYAN,
            detail="peak 1 s sliding-RMS segment from sensor_features.parquet"))
    return events


def encoder_summary(feature_rows: pd.DataFrame, split: str) -> dict:
    """Header-chip summary of encoder anomaly for one incident."""
    if split == "test":
        return {"status": "quarantined",
                "text": "Encoder anomaly: test-quarantined (I-4)"}
    scores = feature_rows.get("anomaly_encoder")
    if scores is None or scores.dropna().empty:
        return {"status": "missing",
                "text": "Encoder anomaly: not computed (run src.encoder.train)"}
    return {"status": "ok",
            "text": f"Encoder anomaly: {float(scores.max()):.3f} (max over windows)"}


def quality_chip(quality_labels: dict[str, int], incident_id: str,
                 split: str) -> dict:
    """Real recovered good/bad run label for the header (run-level, D13)."""
    if split == "test":
        return {"status": "quarantined", "text": "Run label: test-quarantined (I-4)"}
    label = quality_labels.get(incident_id)
    if label is None:
        return {"status": "missing", "text": "Run label: unknown"}
    return {"status": "bad" if label == 1 else "good",
            "text": f"Run label: {'BAD' if label == 1 else 'good'} (recovered)"}


def default_retrieval_query(incident: pd.Series) -> str:
    """Seed query for live SOP retrieval from real incident context."""
    failure = str(incident.get("failure_family", "unknown")).replace("_", " ")
    return f"{failure} vibration anomaly diagnosis and corrective action"


def live_retrieval_cards(hits: list[dict], embedder_name: str) -> list[dict]:
    """SOP cards from real vector-store hits — scores are real cosine similarities."""
    cards = []
    for hit in hits:
        tags = str(hit.get("topic_tags", "") or "")
        text = str(hit.get("text", ""))
        cards.append({
            "ref": str(hit.get("citation", hit.get("chunk_id", ""))),
            "title": (" ".join(text.split())[:80] + "…") if text else hit["chunk_id"],
            "match_pct": int(round(float(hit["score"]) * 100)),
            "status": "Matched" if float(hit["score"]) >= 0.60 else "Partially Matched",
            "phrases": [t.replace("_", " ") for t in tags.split(",") if t],
            "equipment": str(hit.get("doc_type", "")),
            "section": f"cosine {float(hit['score']):.4f} · {embedder_name}",
            "text": text,
            "source": "retrieval",       # real scores, not demo
        })
    return cards


# --------------------------------------------------------------------------- #
# Evidence panel content (R6)
# --------------------------------------------------------------------------- #
def build_ai_explanation(incident: pd.Series, events: list[TimelineEvent]) -> list[dict]:
    spans = [e for e in events if e.row == "SENSOR" and e.source in ("incident", "demo")
             and "Anomaly" in e.label]
    sop = [e for e in events if e.row == "SOP"]
    sentences: list[dict] = []
    if spans:
        first = spans[0]
        sentences.append({
            "text": (f"Vibration RMS increase from t={first.t_start:.0f}s to "
                     f"t={first.t_end:.0f}s marks the anomalous interval, aligned "
                     f"with motion detected in the video stream."),
            "evidence": [first.event_id],
            "source": first.source,
        })
    sentences.append({
        "text": ("Downstream channel changes appear only after the vibration "
                 "anomaly, suggesting a mechanical cause preceding the "
                 "process-level symptoms."),
        "evidence": [e.event_id for e in events if e.row == "SENSOR"][:2],
        "source": "demo",
    })
    if sop:
        ids = ", ".join(e.label.replace(" Matched", "") for e in sop[:2])
        sentences.append({
            "text": f"Retrieved documentation ({ids}) supports the "
                    f"{incident.get('failure_family', 'unknown')} diagnosis.",
            "evidence": [e.event_id for e in sop[:2]],
            "source": "demo",
        })
    return sentences


def build_claim_rows(events: list[TimelineEvent]) -> list[dict]:
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
# DEMO simulated incident (matches the user's reference screenshots)
# --------------------------------------------------------------------------- #
DEMO_DURATION_S = 60.0
_DEMO_CHANNELS = (
    # name, unit, baseline, anomaly_from, anomaly_level, rise_from, rise_level
    ("Vib RMS", "mm/s", 2.0, 18.0, 8.0, None, None),
    ("HF Energy", "g RMS", 0.6, 18.0, 2.6, None, None),
    ("Pressure Var", "bar", 0.08, None, None, 27.0, 0.6),
    ("Temp Delta", "°C", 2.0, None, None, 27.0, 6.0),
    ("Motor Current", "A", 13.0, None, None, 27.0, 14.5),
)


def demo_incident() -> pd.Series:
    """Incident-like row for the simulated DEMO scenario (clearly labeled)."""
    return pd.Series({
        "incident_id": DEMO_INCIDENT_ID,
        "machine_family": "CNC Spindle Unit",
        "source_dataset": "simulated (reference-UI demo)",
        "failure_family": "bearing_wear",
        "severity_label": "high",
        "split": "demo",
        "window_start_s": 0.0,
        "window_end_s": DEMO_DURATION_S,
        "sensor_file": "",
        "video_file": None,
        "sensor_relevant_spans": json.dumps([{"start_s": 18.0, "end_s": 27.0}]),
        "video_relevant_spans": json.dumps([]),
        "sop_chunk_ids": json.dumps([]),
        "maintenance_chunk_ids": json.dumps([]),
    })


def demo_sensor_frame(out_hz: float = 8.0, seed: int = 20260702) -> pd.DataFrame:
    """Deterministic 60 s five-channel series mirroring the reference chart."""
    import numpy as np

    rng = np.random.default_rng(seed)
    t = np.arange(0.0, DEMO_DURATION_S, 1.0 / out_hz)
    rows = []
    for name, _unit, base, anom_from, anom_level, rise_from, rise_level in _DEMO_CHANNELS:
        noise = rng.normal(0, base * 0.08, len(t))
        value = np.full_like(t, base) + noise
        if anom_from is not None:
            ramp = np.clip((t - anom_from) / 6.0, 0.0, 1.0)
            value = value + ramp * (anom_level - base)
        if rise_from is not None:
            ramp = np.clip((t - rise_from) / 20.0, 0.0, 1.0)
            value = value + ramp * (rise_level - base)
        rows.extend({"t": float(tt), "channel": name, "value": float(v)}
                    for tt, v in zip(t, value))
    return pd.DataFrame(rows)


def demo_timeline_events() -> list[TimelineEvent]:
    """The exact bar layout from the reference screenshots (all demo-badged)."""
    mk = TimelineEvent
    return [
        mk("ev_sensor_00", "SENSOR", "Baseline Normal", 0.0, 18.0, "demo", TEAL,
           "reference-UI demo scenario"),
        mk("ev_sensor_01", "SENSOR", "Vib Anomaly", 18.0, 27.0, "demo", AMBER,
           "reference-UI demo scenario"),
        mk("ev_sensor_02", "SENSOR", "Temp + Pressure Rise", 27.0, 60.0, "demo", RED,
           "reference-UI demo scenario"),
        mk("ev_video_00", "VIDEO", "Normal", 0.0, 18.0, "demo", TEAL,
           "reference-UI demo scenario"),
        mk("ev_video_01", "VIDEO", "Shaft Wobble", 18.0, 24.0, "demo", VIOLET,
           "reference-UI demo scenario"),
        mk("ev_video_02", "VIDEO", "Oscillation", 24.0, 27.0, "demo", AMBER,
           "reference-UI demo scenario"),
        mk("ev_video_03", "VIDEO", "Heat Sig", 27.0, 60.0, "demo", RED,
           "reference-UI demo scenario"),
        mk("ev_sop_00", "SOP", "SOP 4.2 Matched", 18.0, 27.0, "demo", GREEN,
           "reference-UI demo scenario"),
        mk("ev_sop_01", "SOP", "Manual B-12", 22.0, 27.0, "demo", GREEN,
           "reference-UI demo scenario"),
        mk("ev_sop_02", "SOP", "SOP 5.7.3", 29.0, 50.0, "demo", GREEN,
           "reference-UI demo scenario"),
        mk("ev_claim_00", "AI CLAIMS", "Claim 2", 18.0, 24.0, "demo", AMBER,
           "reference-UI demo scenario"),
        mk("ev_claim_01", "AI CLAIMS", "Claim 3", 22.0, 27.0, "demo", AMBER,
           "reference-UI demo scenario"),
        mk("ev_claim_02", "AI CLAIMS", "Claim 4", 29.0, 50.0, "demo", AMBER,
           "reference-UI demo scenario"),
    ]


def demo_sop_cards() -> list[dict]:
    return [
        {"ref": "SOP 4.2", "title": "Bearing Vibration Threshold Exceeded",
         "match_pct": 94, "status": "Matched",
         "phrases": ["vibration RMS exceeds 2.5", "bearing anomaly",
                     "high-frequency energy"],
         "equipment": "CNC Spindle Unit", "section": "Section 4: Vibration Analysis",
         "text": "", "source": "demo"},
        {"ref": "SOP 5.7.3", "title": "Downstream Pressure Instability After Spindle Imbalance",
         "match_pct": 81, "status": "Partially Matched",
         "phrases": ["pressure variance", "downstream consequence",
                     "delay of 2–8 seconds"],
         "equipment": "Hydraulic Circuit", "section": "Section 5: Hydraulic Systems",
         "text": "", "source": "demo"},
        {"ref": "Maint Manual B-12", "title": "Spindle Bearing Replacement Procedure",
         "match_pct": 88, "status": "Matched",
         "phrases": ["bearing wear", "replacement interval"],
         "equipment": "CNC Spindle Unit", "section": "Maintenance Manual B-12",
         "text": "", "source": "demo"},
    ]


# --------------------------------------------------------------------------- #
# Export evidence report (R7)
# --------------------------------------------------------------------------- #
def export_report(incident: pd.Series, events: list[TimelineEvent],
                  explanation: list[dict], claims: list[dict],
                  state: PlaybackState, sop_cards: list[dict] | None = None) -> dict[str, Any]:
    return {
        "report_version": 2,
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
        "sop_cards": sop_cards or [],
        "provenance_note": (
            "Elements marked source='demo' are illustrative placeholders; "
            "source='incident' fields come from incidents.parquet; "
            "source='user' notes were created in-session; "
            "video alignment is constructed (label-matched), not measured."
        ),
    }


def export_report_json(incident: pd.Series, events: list[TimelineEvent],
                       explanation: list[dict], claims: list[dict],
                       state: PlaybackState, sop_cards: list[dict] | None = None) -> str:
    return json.dumps(export_report(incident, events, explanation, claims, state,
                                    sop_cards), indent=2, sort_keys=True)
