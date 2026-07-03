"""CNC Incident Workbench — dark industrial UI matching the reference design.

Zones (reference screenshots, 2026-07-03):
  grid     — MACHINE VIDEO STREAM | SENSOR TIME-SERIES | SOP EVIDENCE & EXPLANATION
  wide     — TEMPORAL ALIGNMENT TIMELINE with Play-through / Stop / Export
  details  — incident metadata chips, alignment summary, raw row (preserved)

One unified 0-based incident time axis drives everything: the video transport
readout, the sensor chart cursor, the live readouts, and the timeline cursor
all show the same shared clock (st.session_state, ticked by st.fragment).
A DEMO simulated incident reproduces the reference scenario exactly.
"""

from __future__ import annotations

import time

import altair as alt
import pandas as pd
import streamlit as st

from src.ui.incident_explorer import (
    DEFAULT_PROCESSED_DIR,
    alignment_rows,
    artifact_status,
    find_incident,
    incident_labels,
    incident_text_evidence,
    load_pipeline_tables,
    load_sensor_window,
    repo_root,
    video_path_for_display,
)
from src.ui.workbench import (
    AMBER,
    CYAN,
    DEMO_INCIDENT_ID,
    GREEN,
    RED,
    TIMELINE_ROWS,
    VIOLET,
    PlaybackState,
    build_ai_explanation,
    build_claim_rows,
    build_sop_cards,
    build_timeline_events,
    demo_incident,
    demo_sensor_frame,
    events_frame,
    export_report_json,
    incident_axis,
    live_readouts,
    rolling_rms_frame,
    video_offset_for,
)

st.set_page_config(page_title="CNC Incident Workbench", page_icon="🏭", layout="wide")

TICK_SECONDS = 0.5
PANEL_HEIGHT = 560

CHANNEL_COLORS = {
    "Vib RMS": CYAN, "HF Energy": VIOLET, "Pressure Var": AMBER,
    "Temp Delta": RED, "Motor Current": GREEN,
    "ax RMS": VIOLET, "ay RMS": AMBER, "az RMS": RED,
}
CHANNEL_UNITS = {
    "Vib RMS": "mm/s", "HF Energy": "g RMS", "Pressure Var": "bar",
    "Temp Delta": "°C", "Motor Current": "A",
    "ax RMS": "g", "ay RMS": "g", "az RMS": "g",
}


# --------------------------------------------------------------------------- #
# Styling — dark industrial, white primary text, cyan accents (reference look)
# --------------------------------------------------------------------------- #
def _apply_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container { max-width: 1820px; padding-top: 0.7rem; padding-bottom: 1.2rem; }
        div[data-testid="stVideo"] video {
            max-height: 265px; object-fit: cover; background: #000;
            border: 1px solid #164e63; border-radius: 4px;
        }
        .wb-panel-head {
            display: flex; justify-content: space-between; align-items: baseline;
            border-bottom: 1px solid #1e293b; padding-bottom: 0.3rem; margin-bottom: 0.4rem;
        }
        .wb-h { font-size: 0.86rem; font-weight: 800; letter-spacing: 0.10em;
                color: #ffffff; text-transform: uppercase; }
        .wb-h .acc { color: #22d3ee; }
        .wb-h .dot { color: #ef4444; }
        .wb-meta { font-size: 0.72rem; color: #22d3ee; font-family: monospace; }
        .wb-chip {
            display: inline-block; padding: 0.10rem 0.5rem; margin: 0.12rem 0.22rem 0.12rem 0;
            border-radius: 4px; font-size: 0.72rem; font-weight: 600;
            border: 1px solid #164e63; color: #67e8f9; background: rgba(34,211,238,0.06);
            font-family: monospace;
        }
        .wb-chip.on-amber { border-color: #b45309; color: #fbbf24; background: rgba(251,191,36,0.10); }
        .wb-chip.on-red   { border-color: #b91c1c; color: #f87171; background: rgba(248,113,113,0.10); }
        .wb-chip.demo { border-color: #334155; color: #94a3b8; }
        .wb-clock { font-family: monospace; font-size: 0.9rem; color: #e5e7eb; }
        .wb-read { font-family: monospace; font-size: 0.78rem; color: #e5e7eb;
                   margin-right: 0.9rem; white-space: nowrap; }
        .wb-read b { color: #ffffff; }
        .wb-badge-anom {
            background: rgba(248,113,113,0.15); color: #f87171; border: 1px solid #b91c1c;
            border-radius: 3px; padding: 0 0.3rem; font-size: 0.68rem; font-weight: 700;
        }
        .wb-card {
            border: 1px solid #1e293b; border-radius: 8px; background: #0f172a;
            padding: 0.6rem 0.8rem; margin-bottom: 0.6rem;
        }
        .wb-card .ref { color: #22d3ee; font-family: monospace; font-weight: 700; }
        .wb-card .pct { float: right; color: #e5e7eb; font-family: monospace; }
        .wb-card .title { color: #ffffff; font-weight: 700; margin: 0.15rem 0; }
        .wb-card .foot { color: #64748b; font-size: 0.72rem; }
        .wb-card .foot b { color: #94a3b8; }
        .wb-status { border: 1px solid #0f766e; color: #2dd4bf; border-radius: 4px;
                     padding: 0.05rem 0.45rem; font-size: 0.7rem; font-weight: 700;
                     font-family: monospace; float: right; margin-left: 0.5rem; }
        .wb-status.partial { border-color: #b45309; color: #fbbf24; }
        .wb-phrase {
            display: inline-block; color: #2dd4bf; background: rgba(45,212,191,0.08);
            border: 1px solid #134e4a; border-radius: 3px; padding: 0 0.35rem;
            margin: 0.1rem 0.2rem 0.1rem 0; font-size: 0.72rem; font-family: monospace;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _panel_head(white: str, accent: str, meta: str = "", dot: bool = False) -> None:
    dot_html = '<span class="dot">●</span> ' if dot else ""
    st.markdown(
        f'<div class="wb-panel-head"><span class="wb-h">{dot_html}{white} '
        f'<span class="acc">{accent}</span></span>'
        f'<span class="wb-meta">{meta}</span></div>',
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Cached loaders
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def _load_tables(processed_dir: str):
    return load_pipeline_tables(processed_dir)


@st.cache_data(show_spinner=False)
def _artifact_status(processed_dir: str):
    return artifact_status(processed_dir)


@st.cache_data(show_spinner=False)
def _display_frame(sensor_file: str) -> tuple[pd.DataFrame, float, float, float]:
    """Rolling-RMS display curves + axis for one incident (I-3 feature path)."""
    if sensor_file == "__demo__":
        frame = demo_sensor_frame()
        return frame, 0.0, float(frame["t"].max()), 0.0
    pseudo = pd.Series({"sensor_file": sensor_file})
    _path, sensor_df = load_sensor_window(pseudo, repo_root())
    t0, t1, rel_offset = incident_axis(sensor_df)
    return rolling_rms_frame(sensor_df, rel_offset), t0, t1, rel_offset


# --------------------------------------------------------------------------- #
# Shared playback state (R3)
# --------------------------------------------------------------------------- #
def _init_playback(incident_id: str, t0: float, t1: float) -> None:
    if st.session_state.get("wb_incident") != incident_id:
        st.session_state.wb_incident = incident_id
        st.session_state.wb_current = t0
        st.session_state.wb_playing = False
        st.session_state.wb_rate = 1.0
        st.session_state.wb_selected = None
        st.session_state.wb_last_tick = time.monotonic()
        st.session_state.pop("wb_slider", None)
        st.session_state.pop("wb_jump", None)
    st.session_state.setdefault("wb_notes", {})
    st.session_state.wb_t0, st.session_state.wb_t1 = t0, t1


def _state() -> PlaybackState:
    return PlaybackState(
        t0=st.session_state.wb_t0, t1=st.session_state.wb_t1,
        current_time_s=st.session_state.wb_current,
        is_playing=st.session_state.wb_playing,
        playback_rate=float(st.session_state.wb_rate),
        selected_event_id=st.session_state.wb_selected,
    )


def _store(state: PlaybackState) -> None:
    st.session_state.wb_current = state.current_time_s
    st.session_state.wb_playing = state.is_playing


def _on_play() -> None:
    state = _state()
    state.play()
    _store(state)
    st.session_state.wb_last_tick = time.monotonic()


def _on_stop() -> None:
    state = _state()
    state.stop()
    _store(state)


def _on_scrub() -> None:
    state = _state()
    state.seek(st.session_state.wb_slider)
    state.stop()
    _store(state)


def _on_step(dt: float) -> None:
    state = _state()
    state.step(dt)
    state.stop()
    _store(state)


def _on_snapshot() -> None:
    state = _state()
    notes = st.session_state.wb_notes.setdefault(st.session_state.wb_incident, [])
    notes.append({"t": state.current_time_s,
                  "label": f"Snapshot @ {state.current_time_s:.0f}s"})


def _user_notes() -> list[dict]:
    return st.session_state.wb_notes.get(st.session_state.get("wb_incident", ""), [])


# --------------------------------------------------------------------------- #
# Video panel (R4)
# --------------------------------------------------------------------------- #
def _clip_duration(incident: pd.Series, video_index: pd.DataFrame) -> float:
    if not video_index.empty and "video_file" in video_index.columns:
        match = video_index[video_index["video_file"] == incident.get("video_file")]
        if not match.empty and "duration_s" in match.columns:
            return float(match["duration_s"].iloc[0])
    return 7.0


def _demo_video_path(video_index: pd.DataFrame):
    if video_index.empty or "video_file" not in video_index.columns:
        return None
    pseudo = pd.Series({"video_file": video_index["video_file"].iloc[0]})
    return video_path_for_display(pseudo, repo_root())


def _render_video_panel(incident: pd.Series, state: PlaybackState, events,
                        video_index: pd.DataFrame, is_demo: bool) -> None:
    _panel_head("MACHINE", "VIDEO STREAM",
                meta="CAM-001 · 720p · 30fps" + (" · demo stream" if is_demo else ""),
                dot=True)
    video_path = (_demo_video_path(video_index) if is_demo
                  else video_path_for_display(incident, repo_root()))
    if video_path is None or not video_path.exists():
        st.info("No linked video for this incident.")
    else:
        clip_duration = (_clip_duration(incident, video_index) if not is_demo
                         else _clip_duration(pd.Series(
                             {"video_file": video_index["video_file"].iloc[0]}), video_index))
        offset = video_offset_for(state, clip_duration)
        st.video(str(video_path), start_time=int(offset),
                 autoplay=state.is_playing, muted=True)
    chips = []
    for e in [ev for ev in events if ev.row == "VIDEO"]:
        cls = ""
        if e.contains(state.current_time_s):
            cls = "on-red" if e.color == RED else "on-amber"
        chips.append(f'<span class="wb-chip {cls}">t= {e.t_start:.0f} s · {e.label}</span>')
    st.markdown(" ".join(chips), unsafe_allow_html=True)

    back, play, fwd, slider_col, timec, rate, snap = st.columns(
        [0.06, 0.07, 0.06, 0.35, 0.14, 0.12, 0.20], vertical_alignment="bottom")
    with back:
        st.button("↞", on_click=_on_step, args=(-1.0,), help="Step back 1 s")
    with play:
        if state.is_playing:
            st.button("⏸", on_click=_on_stop, help="Pause")
        else:
            st.button("▶", on_click=_on_play, help="Play")
    with fwd:
        st.button("↠", on_click=_on_step, args=(1.0,), help="Step forward 1 s")
    with slider_col:
        if "wb_slider" not in st.session_state:
            st.session_state.wb_slider = state.current_time_s
        st.slider("cursor", min_value=state.t0, max_value=state.t1, step=0.1,
                  key="wb_slider", on_change=_on_scrub, label_visibility="collapsed")
    with timec:
        st.markdown(f'<span class="wb-clock">{state.current_time_s:.0f}s / '
                    f'{state.t1:.0f}s</span>', unsafe_allow_html=True)
    with rate:
        st.selectbox("rate", options=[0.5, 1.0, 2.0], key="wb_rate",
                     format_func=lambda r: f"{r:g}×", label_visibility="collapsed")
    with snap:
        st.button("⤢ Snapshot", on_click=_on_snapshot,
                  help="Drop a note on the timeline at the current cursor")


# --------------------------------------------------------------------------- #
# Sensor panel (R5)
# --------------------------------------------------------------------------- #
def _sensor_chart(display: pd.DataFrame, events, state: PlaybackState,
                  readouts: list[dict]) -> alt.LayerChart:
    x_scale = alt.Scale(domain=[state.t0, state.t1])
    channels = list(display["channel"].unique())
    color_range = [CHANNEL_COLORS.get(c, "#94a3b8") for c in channels]
    layers: list = []
    regions = [e for e in events
               if e.row == "SENSOR" and e.label != "Baseline Normal"]
    if regions:
        region_frame = pd.DataFrame([{
            "t_start": e.t_start, "t_end": e.t_end, "label": e.label.upper(),
            "color": e.color} for e in regions])
        layers.append(alt.Chart(region_frame).mark_rect(opacity=0.12).encode(
            x=alt.X("t_start:Q", scale=x_scale), x2="t_end:Q",
            color=alt.Color("color:N", scale=None),
            tooltip=["label", "t_start", "t_end"]))
        layers.append(alt.Chart(region_frame).mark_text(
            align="left", dx=3, dy=8, baseline="top", fontSize=9, fontWeight="bold").encode(
            x=alt.X("t_start:Q", scale=x_scale), y=alt.value(0),
            text="label:N", color=alt.Color("color:N", scale=None)))
    thresholds = pd.DataFrame(
        [{"y": r["threshold"], "channel": r["channel"]}
         for r in readouts if pd.notna(r["threshold"])][:2])
    if not thresholds.empty:
        layers.append(alt.Chart(thresholds).mark_rule(
            strokeDash=[5, 5], opacity=0.6).encode(
            y="y:Q",
            color=alt.Color("channel:N",
                            scale=alt.Scale(domain=channels, range=color_range),
                            legend=None),
            tooltip=[alt.Tooltip("y:Q", title="THRESH"), "channel:N"]))
    layers.append(alt.Chart(display).mark_line(strokeWidth=1.6).encode(
        x=alt.X("t:Q", title="TIME (seconds)", scale=x_scale),
        y=alt.Y("value:Q", title=None),
        color=alt.Color("channel:N",
                        scale=alt.Scale(domain=channels, range=color_range),
                        legend=None),
    ))
    cursor = pd.DataFrame({"t": [state.current_time_s]})
    layers.append(alt.Chart(cursor).mark_rule(color=CYAN, strokeWidth=2).encode(
        x=alt.X("t:Q", scale=x_scale)))
    layers.append(alt.Chart(cursor).mark_point(
        color=CYAN, filled=True, size=70, yOffset=-4).encode(
        x=alt.X("t:Q", scale=x_scale), y=alt.value(0)))
    return alt.layer(*layers).properties(height=300)


def _render_readouts(readouts: list[dict], t: float) -> None:
    parts = []
    for r in readouts:
        color = CHANNEL_COLORS.get(r["channel"], "#94a3b8")
        unit = CHANNEL_UNITS.get(r["channel"], "")
        badge = ' <span class="wb-badge-anom">ANOMALY</span>' if r["anomaly"] else ""
        parts.append(
            f'<span class="wb-read"><span style="color:{color}">●</span> '
            f'{r["channel"]}: <b>{r["value"]:.2f}</b> {unit}{badge}</span>')
    parts.append(f'<span class="wb-read" style="float:right">t = {t:.0f}s</span>')
    st.markdown("<div>" + "".join(parts) + "</div>", unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# SOP / AI / Claims panel (R6)
# --------------------------------------------------------------------------- #
def _render_sop_cards(cards: list[dict]) -> None:
    if not cards:
        st.info("No linked SOP/maintenance chunks.")
        return
    for card in cards:
        status_cls = "" if card["status"] == "Matched" else "partial"
        phrases = "".join(f'<span class="wb-phrase">"{p}"</span>' for p in card["phrases"])
        demo_badge = (' <span class="wb-chip demo">match % demo</span>'
                      if card["source"] == "demo" else "")
        st.markdown(
            f"""
            <div class="wb-card">
              <span class="ref">{card["ref"]}</span>
              <span class="wb-status {status_cls}">{card["status"]}</span>
              <span class="pct">{card["match_pct"]}%</span>
              <div class="title">{card["title"]}</div>
              <div>Matched phrases: {phrases}</div>
              <div class="foot">Equipment: <b>{card["equipment"]}</b> ·
                   {card["section"]}{demo_badge}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if card.get("text"):
            with st.expander("chunk text"):
                st.write(card["text"])


def _render_evidence_panel(incident: pd.Series, cards: list[dict],
                           events, state: PlaybackState) -> None:
    _panel_head("SOP EVIDENCE &", "EXPLANATION")
    sop_tab, ai_tab, claims_tab = st.tabs(["SOP Evidence", "AI Explanation",
                                           "Claim Verification"])
    with sop_tab:
        box = st.container(height=400, border=False)
        with box:
            _render_sop_cards(cards)
    with ai_tab:
        for sentence in build_ai_explanation(incident, events):
            badge = "" if sentence["source"] == "incident" else "  `demo`"
            refs = (" — evidence: " + ", ".join(sentence["evidence"])) if sentence["evidence"] else ""
            st.markdown(f"- {sentence['text']}{badge}{refs}")
    with claims_tab:
        claims = build_claim_rows(events)
        if claims:
            st.dataframe(pd.DataFrame(claims), hide_index=True, width="stretch")
        else:
            st.info("No claims for this incident.")
        st.caption("Real claim verification arrives with the decoder + verifier "
                   "(Build Phases 11–12).")


# --------------------------------------------------------------------------- #
# Temporal alignment timeline (R2)
# --------------------------------------------------------------------------- #
def _timeline_chart(frame: pd.DataFrame, state: PlaybackState) -> alt.LayerChart:
    x_scale = alt.Scale(domain=[state.t0, state.t1])
    y = alt.Y("row:N", sort=list(TIMELINE_ROWS), title=None,
              axis=alt.Axis(labelColor="#94a3b8", labelFontWeight="bold",
                            labelFontSize=11, ticks=False, domain=False))
    bars = alt.Chart(frame).mark_bar(cornerRadius=3, height=18,
                                     stroke=None).encode(
        y=y,
        x=alt.X("t_start:Q", title=None, scale=x_scale,
                axis=alt.Axis(format="~s", labelExpr="datum.value + 's'",
                              labelColor="#64748b", grid=True, gridColor="#1e293b")),
        x2="t_end:Q",
        color=alt.Color("color:N", scale=None),
        opacity=alt.condition(alt.datum.active, alt.value(0.50), alt.value(0.22)),
        tooltip=["display_label:N", "t_start:Q", "t_end:Q", "source:N", "detail:N"],
    )
    outlines = alt.Chart(frame).mark_bar(cornerRadius=3, height=18,
                                         filled=False, strokeWidth=1.4).encode(
        y=y, x=alt.X("t_start:Q", scale=x_scale), x2="t_end:Q",
        stroke=alt.Color("color:N", scale=None),
        opacity=alt.condition(alt.datum.active, alt.value(1.0), alt.value(0.6)),
    )
    labels = alt.Chart(frame).mark_text(
        align="left", dx=5, fontSize=10, fontWeight="bold").encode(
        y=y, x=alt.X("t_start:Q", scale=x_scale),
        text="label:N", color=alt.Color("color:N", scale=None),
    )
    cursor = alt.Chart(pd.DataFrame({"t": [state.current_time_s]})).mark_rule(
        color=CYAN, strokeWidth=2).encode(x=alt.X("t:Q", scale=x_scale))
    return alt.layer(bars, outlines, labels, cursor).properties(height=225)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    _apply_styles()

    with st.sidebar:
        st.header("Dataset")
        processed_dir = st.text_input("Processed data folder",
                                      value=DEFAULT_PROCESSED_DIR.as_posix())
        if st.button("Refresh data", width="stretch"):
            st.cache_data.clear()
        st.dataframe(_artifact_status(processed_dir), hide_index=True, width="stretch")

    tables = _load_tables(processed_dir)
    incidents = tables.incidents
    if incidents.empty:
        st.error("No incidents.parquet found. Run the pipeline first.")
        st.code("python -m src.cli all --config config/dataset.yaml", language="bash")
        return

    labels = incident_labels(incidents)
    labels = {DEMO_INCIDENT_ID: "🎬 DEMO — simulated incident (reference-UI scenario)",
              **labels}
    selected = st.selectbox("Choose an incident", options=list(labels.keys()),
                            format_func=lambda inc_id: labels.get(inc_id, inc_id),
                            key="main_incident_selector")
    is_demo = selected == DEMO_INCIDENT_ID
    incident = demo_incident() if is_demo else find_incident(incidents, selected)

    # ---- unified 0-based incident time axis ----
    sensor_key = "__demo__" if is_demo else str(incident["sensor_file"])
    display, t0, t1, rel_offset = _display_frame(sensor_key)
    _init_playback(selected, t0, t1)
    state = _state()

    events = build_timeline_events(incident, t0, t1, rel_offset=rel_offset,
                                   user_notes=_user_notes())
    if is_demo:
        cards = build_sop_cards(incident, pd.DataFrame(), pd.DataFrame())
    else:
        sop_chunks, maint_chunks = incident_text_evidence(incident, tables.text_chunks)
        cards = build_sop_cards(incident, sop_chunks, maint_chunks)
    explanation = build_ai_explanation(incident, events)
    claims = build_claim_rows(events)

    # ---- main grid ----
    video_col, sensor_col, evidence_col = st.columns([0.30, 0.38, 0.32], gap="small")
    with video_col, st.container(border=True, height=PANEL_HEIGHT):
        _render_video_panel(incident, state, events, tables.video_index, is_demo)
        state = _state()  # transport may have mutated the shared clock
    with evidence_col, st.container(border=True, height=PANEL_HEIGHT):
        _render_evidence_panel(incident, cards, events, state)
    with sensor_col, st.container(border=True, height=PANEL_HEIGHT):
        channels = list(display["channel"].unique())
        default = [c for c in ("Vib RMS", "Pressure Var", "Temp Delta") if c in channels] \
            or channels[:3]
        _panel_head("SENSOR", "TIME-SERIES")
        chosen = st.pills("channels", options=channels, default=default,
                          selection_mode="multi", key=f"wb_ch_{selected}",
                          label_visibility="collapsed")
        subset = display[display["channel"].isin(chosen)] if chosen else display.head(0)

        @st.fragment(run_every=TICK_SECONDS)
        def _sensor_live() -> None:
            live = _state()
            if live.is_playing:
                now = time.monotonic()
                live.tick(now - st.session_state.wb_last_tick)
                st.session_state.wb_last_tick = now
                _store(live)
            if subset.empty:
                st.info("Select at least one channel.")
                return
            readouts = live_readouts(subset, live.current_time_s)
            st.altair_chart(_sensor_chart(subset, events, live, readouts),
                            width="stretch")
            _render_readouts(readouts, live.current_time_s)

        _sensor_live()

    # ---- temporal alignment timeline ----
    head_l, play_c, stop_c, export_c = st.columns([0.55, 0.13, 0.10, 0.22],
                                                  vertical_alignment="center")
    with head_l:
        _panel_head("TEMPORAL ALIGNMENT", "TIMELINE")
    with play_c:
        st.button("▷ Play-through", on_click=_on_play, width="stretch",
                  disabled=state.is_playing)
    with stop_c:
        st.button("⏸ Stop", on_click=_on_stop, width="stretch",
                  disabled=not state.is_playing)
    with export_c:
        st.download_button("⬇ Export Evidence Report",
                           data=export_report_json(incident, events, explanation,
                                                   claims, _state(), cards),
                           file_name=f"{selected}_evidence_report.json",
                           mime="application/json", width="stretch")

    @st.fragment(run_every=TICK_SECONDS)
    def _timeline_live() -> None:
        live = _state()
        st.altair_chart(_timeline_chart(events_frame(events, live.current_time_s), live),
                        width="stretch")

    _timeline_live()

    # ---- details (preserved explorer functionality) ----
    with st.expander("Incident details · alignment summary · raw row"):
        sev = str(incident.get("severity_label", "unknown"))
        st.markdown(
            f'<span class="wb-chip">Incident: {selected}</span>'
            f'<span class="wb-chip">Equipment: {incident.get("machine_family", "?")}</span>'
            f'<span class="wb-chip">Failure: {incident.get("failure_family", "?")}</span>'
            f'<span class="wb-chip {"on-red" if sev == "high" else "on-amber"}">'
            f'Severity: {sev}</span>'
            f'<span class="wb-chip">Split: {incident.get("split", "?")}</span>'
            f'<span class="wb-chip demo">Confidence: 0.82 (demo)</span>'
            f'<span class="wb-chip demo">Hallucination risk: LOW (demo)</span>',
            unsafe_allow_html=True)
        align_tab, row_tab = st.tabs(["Alignment", "Raw Row"])
        with align_tab:
            if is_demo:
                st.info("Simulated demo incident — no dataset alignment row.")
            else:
                st.dataframe(alignment_rows(incident), hide_index=True, width="stretch")
                st.info("The sensor window is the temporal anchor. Video and text are "
                        "linked by matching/retrieval heuristics — relevant evidence, "
                        "not physically synchronized ground truth.")
        with row_tab:
            st.dataframe(incident.to_frame("value").astype({"value": "string"}),
                         width="stretch")


if __name__ == "__main__":
    main()
