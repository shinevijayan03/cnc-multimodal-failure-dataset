"""CNC Incident Workbench — dark industrial explorer with temporal alignment.

Layout (UI temporal alignment refactor):
  header   — incident metadata chips + export evidence report
  controls — play-through / stop / rate / scrub / jump-to-event
  grid     — video stream | sensor time-series | SOP / AI / claims panel
  wide     — temporal alignment timeline (SENSOR / VIDEO / SOP / AI CLAIMS / NOTES)
  details  — alignment summary + raw incident row (preserved from the explorer)

Shared playback state lives in st.session_state and is advanced by a
`st.fragment(run_every=...)` clock, so the sensor cursor and timeline cursor
stay synchronized. The video element follows the shared clock via
start_time/autoplay on rerun (Streamlit's st.video cannot report its own time
back — documented limitation).
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
    available_sensor_channels,
    decode_list_cell,
    find_incident,
    incident_labels,
    incident_text_evidence,
    load_pipeline_tables,
    load_sensor_window,
    repo_root,
    sensor_plot_frame,
    video_path_for_display,
)
from src.ui.workbench import (
    ROW_COLORS,
    TIMELINE_ROWS,
    PlaybackState,
    active_events,
    build_ai_explanation,
    build_claim_rows,
    build_timeline_events,
    events_frame,
    export_report_json,
    video_offset_for,
)

st.set_page_config(page_title="CNC Incident Workbench", page_icon="🏭", layout="wide")

TICK_SECONDS = 0.5


# --------------------------------------------------------------------------- #
# Styling
# --------------------------------------------------------------------------- #
def _apply_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container { max-width: 1780px; padding-top: 0.9rem; padding-bottom: 1.5rem; }
        div[data-testid="stVideo"] video {
            max-height: 300px; object-fit: contain; background: #000; border-radius: 8px;
        }
        .wb-header {
            background: linear-gradient(90deg, #111827 0%, #0f172a 100%);
            border: 1px solid #1f2937; border-radius: 10px;
            padding: 0.7rem 1.0rem; margin-bottom: 0.4rem;
        }
        .wb-title { font-size: 1.25rem; font-weight: 700; color: #f3f4f6; }
        .wb-sub { color: #9ca3af; font-size: 0.8rem; }
        .wb-chip {
            display: inline-block; padding: 0.12rem 0.55rem; margin: 0.1rem 0.18rem 0.1rem 0;
            border-radius: 999px; font-size: 0.74rem; font-weight: 600;
            border: 1px solid #374151; color: #e5e7eb; background: #1f2937;
        }
        .wb-chip.warn { border-color: #b45309; color: #fbbf24; }
        .wb-chip.bad  { border-color: #b91c1c; color: #f87171; }
        .wb-chip.good { border-color: #047857; color: #34d399; }
        .wb-chip.demo { border-color: #4b5563; color: #9ca3af; font-style: italic; }
        .wb-panel-title {
            font-size: 0.78rem; letter-spacing: 0.08em; font-weight: 700;
            color: #93c5fd; text-transform: uppercase; margin-bottom: 0.2rem;
        }
        .wb-clock { font-family: monospace; font-size: 0.95rem; color: #fbbf24; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Cached loaders (unchanged behavior from the explorer)
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def _load_tables(processed_dir: str):
    return load_pipeline_tables(processed_dir)


@st.cache_data(show_spinner=False)
def _artifact_status(processed_dir: str):
    return artifact_status(processed_dir)


@st.cache_data(show_spinner=False)
def _load_sensor(sensor_file: str):
    pseudo_incident = pd.Series({"sensor_file": sensor_file})
    path, frame = load_sensor_window(pseudo_incident, repo_root())
    return path, frame


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
    st.session_state.wb_t0, st.session_state.wb_t1 = t0, t1


def _state() -> PlaybackState:
    return PlaybackState(
        t0=st.session_state.wb_t0, t1=st.session_state.wb_t1,
        current_time_s=st.session_state.wb_current,
        is_playing=st.session_state.wb_playing,
        playback_rate=st.session_state.wb_rate,
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


# --------------------------------------------------------------------------- #
# Panels
# --------------------------------------------------------------------------- #
def _render_header(incident: pd.Series, incident_id: str, report_json: str) -> None:
    meta, export_col = st.columns([0.84, 0.16], vertical_alignment="center")
    severity = str(incident.get("severity_label", "unknown"))
    sev_cls = {"high": "bad", "med": "warn", "low": "good"}.get(severity, "")
    with meta:
        st.markdown(
            f"""
            <div class="wb-header">
              <span class="wb-title">🏭 CNC Incident Workbench</span>
              <span class="wb-sub"> · incident <code>{incident_id}</code></span><br/>
              <span class="wb-chip">Equipment: {incident.get("machine_family", "unknown")}</span>
              <span class="wb-chip">Dataset: {incident.get("source_dataset", "unknown")}</span>
              <span class="wb-chip">Window: {float(incident.get("window_start_s", 0)):.1f}s → {float(incident.get("window_end_s", 0)):.1f}s</span>
              <span class="wb-chip warn">Failure: {incident.get("failure_family", "unknown")}</span>
              <span class="wb-chip {sev_cls}">Severity: {severity}</span>
              <span class="wb-chip demo">Confidence: 0.82 (demo)</span>
              <span class="wb-chip demo">Hallucination risk: LOW (demo)</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with export_col:
        st.download_button(
            "⬇️ Export evidence report",
            data=report_json,
            file_name=f"{incident_id}_evidence_report.json",
            mime="application/json",
            width="stretch",
        )


def _render_controls(state: PlaybackState, events) -> None:
    play_col, stop_col, rate_col, slider_col, jump_col = st.columns(
        [0.10, 0.08, 0.10, 0.47, 0.25], vertical_alignment="bottom")
    with play_col:
        st.button("▶ Play-through", on_click=_on_play, width="stretch",
                  disabled=state.is_playing)
    with stop_col:
        st.button("⏹ Stop", on_click=_on_stop, width="stretch",
                  disabled=not state.is_playing)
    with rate_col:
        st.selectbox("Rate", options=[0.5, 1.0, 2.0], key="wb_rate", format_func=lambda r: f"{r}×")
    with slider_col:
        if "wb_slider" not in st.session_state:
            st.session_state.wb_slider = state.current_time_s
        st.slider("Cursor (incident-relative s)", min_value=state.t0, max_value=state.t1,
                  step=0.1, key="wb_slider", on_change=_on_scrub)
    with jump_col:
        options = [""] + [e.event_id for e in events]
        labels = {e.event_id: f"{e.row}: {e.label[:40]}" for e in events}
        chosen = st.selectbox("Jump to event", options=options,
                              format_func=lambda x: labels.get(x, "—"),
                              key="wb_jump")
        if chosen and chosen != st.session_state.wb_selected:
            st.session_state.wb_selected = chosen
            target = next(e for e in events if e.event_id == chosen)
            state.seek(target.t_start)
            state.stop()
            _store(state)


def _clip_duration(incident: pd.Series, video_index: pd.DataFrame) -> float:
    """Clip duration from video_index.parquet; 7.0 s fallback if unmatched."""
    if not video_index.empty and "video_file" in video_index.columns:
        match = video_index[video_index["video_file"] == incident.get("video_file")]
        if not match.empty and "duration_s" in match.columns:
            return float(match["duration_s"].iloc[0])
    return 7.0


def _render_video_panel(incident: pd.Series, state: PlaybackState, events,
                        video_index: pd.DataFrame) -> None:
    st.markdown('<div class="wb-panel-title">Machine video stream</div>',
                unsafe_allow_html=True)
    video_path = video_path_for_display(incident, repo_root())
    if video_path is None:
        st.info("This incident has no linked video.")
        return
    if not video_path.exists():
        st.error(f"Video file referenced but missing: {video_path}")
        return
    clip_duration = _clip_duration(incident, video_index)
    offset = video_offset_for(state, clip_duration)
    st.video(str(video_path), start_time=int(offset),
             autoplay=state.is_playing, muted=True)
    st.caption(
        f"clip offset ≈ {offset:04.1f}s / {clip_duration:.1f}s · follows the shared "
        f"cursor (proportional mapping; sync provenance: constructed)")
    chips = []
    for e in [ev for ev in events if ev.row == "VIDEO"]:
        cls = "warn" if e.contains(state.current_time_s) else "demo"
        chips.append(f'<span class="wb-chip {cls}">{e.label} '
                     f'({e.t_start:.0f}s–{e.t_end:.0f}s)</span>')
    st.markdown(" ".join(chips), unsafe_allow_html=True)


def _sensor_chart(long_frame: pd.DataFrame, x_col: str, spans: list[tuple[float, float]],
                  state: PlaybackState) -> alt.LayerChart:
    x_scale = alt.Scale(domain=[state.t0, state.t1])
    lines = alt.Chart(long_frame).mark_line(strokeWidth=1).encode(
        x=alt.X(f"{x_col}:Q", title="incident-relative time (s)", scale=x_scale),
        y=alt.Y("value:Q", title="acceleration"),
        color=alt.Color("channel:N", legend=alt.Legend(orient="top", title=None)),
    )
    layers: list = [lines]
    if spans:
        span_frame = pd.DataFrame(
            [{"t_start": lo, "t_end": hi, "kind": "vibration anomaly (evidence)"}
             for lo, hi in spans])
        layers.insert(0, alt.Chart(span_frame).mark_rect(opacity=0.16, color="#f59e0b").encode(
            x=alt.X("t_start:Q", scale=x_scale), x2="t_end:Q",
            tooltip=["kind", "t_start", "t_end"]))
    cursor_frame = pd.DataFrame({"t": [state.current_time_s]})
    layers.append(alt.Chart(cursor_frame).mark_rule(color="#fbbf24", strokeWidth=2).encode(
        x=alt.X("t:Q", scale=x_scale)))
    return alt.layer(*layers).properties(height=280)


def _timeline_chart(frame: pd.DataFrame, state: PlaybackState) -> alt.LayerChart:
    x_scale = alt.Scale(domain=[state.t0, state.t1])
    row_scale = alt.Scale(domain=list(TIMELINE_ROWS),
                          range=[ROW_COLORS[r] for r in TIMELINE_ROWS])
    bars = alt.Chart(frame).mark_bar(cornerRadius=3, height=16).encode(
        y=alt.Y("row:N", sort=list(TIMELINE_ROWS), title=None),
        x=alt.X("t_start:Q", title="incident-relative time (s)", scale=x_scale),
        x2="t_end:Q",
        color=alt.Color("row:N", scale=row_scale, legend=None),
        opacity=alt.condition(alt.datum.active, alt.value(1.0), alt.value(0.40)),
        tooltip=["display_label:N", "t_start:Q", "t_end:Q", "source:N", "detail:N"],
    )
    labels = alt.Chart(frame).mark_text(
        align="left", dx=3, dy=-13, fontSize=10, color="#cbd5e1").encode(
        y=alt.Y("row:N", sort=list(TIMELINE_ROWS)),
        x=alt.X("t_start:Q", scale=x_scale),
        text="display_label:N",
    )
    cursor = alt.Chart(pd.DataFrame({"t": [state.current_time_s]})).mark_rule(
        color="#fbbf24", strokeWidth=2).encode(x=alt.X("t:Q", scale=x_scale))
    return alt.layer(bars, labels, cursor).properties(height=230)


def _render_evidence_panel(incident: pd.Series, text_chunks: pd.DataFrame,
                           events, state: PlaybackState) -> None:
    sop_tab, ai_tab, claims_tab = st.tabs(["SOP Evidence", "AI Explanation",
                                           "Claim Verification"])
    with sop_tab:
        sop_chunks, maint_chunks = incident_text_evidence(incident, text_chunks)
        box = st.container(height=330, border=False)
        with box:
            for title, chunks in (("SOP", sop_chunks), ("Maintenance", maint_chunks)):
                st.markdown(f"**{title}**")
                if chunks.empty:
                    st.caption("No linked chunks.")
                    continue
                for i, (_, chunk) in enumerate(chunks.iterrows(), start=1):
                    tags = decode_list_cell(chunk.get("topic_tags"))
                    with st.expander(f"{chunk['chunk_id']} · {chunk.get('n_tokens', 0)} tokens",
                                     expanded=(title == "SOP" and i == 1)):
                        if tags:
                            st.caption("Topics: " + ", ".join(map(str, tags)))
                        st.write(str(chunk.get("text", "")).strip())
    with ai_tab:
        for sentence in build_ai_explanation(incident, events):
            badge = "" if sentence["source"] == "incident" else "  `demo`"
            refs = (" — evidence: " + ", ".join(sentence["evidence"])) if sentence["evidence"] else ""
            st.markdown(f"- {sentence['text']}{badge}{refs}")
        act = active_events(events, state.current_time_s)
        if act:
            st.caption("Active at cursor: " + " · ".join(e.label for e in act[:4]))
    with claims_tab:
        claims = build_claim_rows(events)
        if claims:
            st.dataframe(pd.DataFrame(claims), hide_index=True, width="stretch")
        else:
            st.info("No claims for this incident.")
        st.caption("Real claim verification arrives with the decoder + verifier "
                   "(Build Phases 11–12); statuses above are span-level only.")


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
        status = _artifact_status(processed_dir)
        st.dataframe(status, hide_index=True, width="stretch")
        max_points = st.slider("Sensor chart max points", 500, 10000, 3000, 500)

    tables = _load_tables(processed_dir)
    incidents = tables.incidents
    if incidents.empty:
        st.error("No incidents.parquet found. Run the pipeline first.")
        st.code("python -m src.cli all --config config/dataset.yaml", language="bash")
        return

    labels = incident_labels(incidents)
    selected = st.selectbox("Choose an incident", options=list(labels.keys()),
                            format_func=lambda inc_id: labels.get(inc_id, inc_id),
                            key="main_incident_selector")
    incident = find_incident(incidents, selected)

    # ---- shared time axis from the sensor waveform (the temporal anchor) ----
    _sensor_path, sensor_df = _load_sensor(str(incident["sensor_file"]))
    x_col = "t_rel_s" if "t_rel_s" in sensor_df.columns else "time_s"
    t0 = float(sensor_df[x_col].min()) if not sensor_df.empty else 0.0
    t1 = float(sensor_df[x_col].max()) if not sensor_df.empty else 1.0
    _init_playback(selected, t0, t1)
    state = _state()

    events = build_timeline_events(incident, t0, t1)
    explanation = build_ai_explanation(incident, events)
    claims = build_claim_rows(events)
    report_json = export_report_json(incident, events, explanation, claims, state)

    _render_header(incident, selected, report_json)
    _render_controls(state, events)
    state = _state()  # controls may have mutated session state

    # ---- main grid ----
    video_col, sensor_col, evidence_col = st.columns([0.30, 0.38, 0.32], gap="medium")
    with video_col, st.container(border=True, height=470):
        _render_video_panel(incident, state, events, tables.video_index)
    with evidence_col, st.container(border=True, height=470):
        st.markdown('<div class="wb-panel-title">SOP · AI explanation · claims</div>',
                    unsafe_allow_html=True)
        _render_evidence_panel(incident, tables.text_chunks, events, state)

    channels = available_sensor_channels(sensor_df)
    with sensor_col, st.container(border=True, height=470):
        st.markdown('<div class="wb-panel-title">Sensor time-series</div>',
                    unsafe_allow_html=True)
        chosen = st.multiselect("Channels", options=channels, default=channels[:3],
                                key=f"wb_channels_{selected}")
        plot_frame = sensor_plot_frame(sensor_df, chosen, max_points=max_points)
        spans = [(e.t_start, e.t_end) for e in events
                 if e.row == "SENSOR" and e.source == "incident"]
        long_frame = (plot_frame.reset_index()
                      .melt(id_vars=x_col, var_name="channel", value_name="value")
                      if not plot_frame.empty and chosen else pd.DataFrame())

        @st.fragment(run_every=TICK_SECONDS)
        def _sensor_live() -> None:
            live = _state()
            if live.is_playing:
                now = time.monotonic()
                live.tick(now - st.session_state.wb_last_tick)
                st.session_state.wb_last_tick = now
                _store(live)
            st.markdown(
                f'<span class="wb-clock">t = {live.current_time_s:+06.2f}s '
                f'/ [{live.t0:+.1f}s … {live.t1:+.1f}s] '
                f'{"▶ playing" if live.is_playing else "⏹ stopped"} '
                f'@ {live.playback_rate}×</span>',
                unsafe_allow_html=True,
            )
            if long_frame.empty:
                st.info("No numeric sensor channels selected.")
            else:
                st.altair_chart(_sensor_chart(long_frame, x_col, spans, live),
                                use_container_width=True)

        _sensor_live()

    # ---- temporal alignment timeline (full width) ----
    st.markdown('<div class="wb-panel-title">Temporal alignment timeline</div>',
                unsafe_allow_html=True)

    @st.fragment(run_every=TICK_SECONDS)
    def _timeline_live() -> None:
        live = _state()
        frame = events_frame(events, live.current_time_s)
        st.altair_chart(_timeline_chart(frame, live), width="stretch")
        legend = " ".join(
            f'<span class="wb-chip" style="border-color:{ROW_COLORS[r]};'
            f'color:{ROW_COLORS[r]}">{r}</span>' for r in TIMELINE_ROWS)
        st.markdown(legend + '<span class="wb-chip demo">demo bars are placeholders '
                             'until Phases 7–11</span>', unsafe_allow_html=True)

    _timeline_live()

    # ---- preserved explorer details ----
    with st.expander("Alignment summary & raw incident row"):
        align_tab, row_tab = st.tabs(["Alignment", "Raw Row"])
        with align_tab:
            st.dataframe(alignment_rows(incident), hide_index=True, width="stretch")
            st.info("The sensor window is the temporal anchor. Video and text are "
                    "linked by matching/retrieval heuristics — relevant evidence, "
                    "not physically synchronized ground truth.")
        with row_tab:
            st.dataframe(incident.to_frame("value").astype({"value": "string"}),
                         width="stretch")


if __name__ == "__main__":
    main()
