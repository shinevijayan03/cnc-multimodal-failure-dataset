"""CNC Incident Workbench — dark industrial UI matching the reference design.

Zones (reference screenshots, 2026-07-03):
  grid     — MACHINE VIDEO STREAM | SENSOR TIME-SERIES | SOP EVIDENCE & EXPLANATION
  wide     — TEMPORAL ALIGNMENT TIMELINE with Play-through / Stop / Export
  details  — incident metadata chips, alignment summary, raw row (preserved)

One unified 0-based incident time axis drives everything: the video element,
the sensor chart cursor, the live readouts, and the timeline cursor all follow
the same shared clock (st.session_state, ticked by st.fragment). The video is
an HTML5 component driven proportionally against the global clock (constructed
sync, I-8), so play-through always reaches the final timeline tick — never the
clip's native duration. Clicking a timeline evidence bar seeks every view.
A DEMO simulated incident reproduces the reference scenario exactly.
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import asdict

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

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
    default_retrieval_query,
    demo_incident,
    demo_sensor_frame,
    encoder_summary,
    events_frame,
    export_report_json,
    grounded_explanation,
    grounded_sop_events,
    important_interval_events,
    incident_axis,
    incident_bundle,
    incident_explanation,
    incident_feature_rows,
    incident_tuples,
    live_readouts,
    live_retrieval_cards,
    quality_chip,
    evidence_jump_options,
    rolling_rms_frame,
    video_summary_for,
    video_sync_spec,
    vlm_video_events,
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
# Styling — light theme matching the original explorer look (white bg, dark text)
# --------------------------------------------------------------------------- #
def _apply_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container { max-width: 1820px; padding-top: 0.7rem; padding-bottom: 1.2rem; }
        div[data-testid="stVideo"] video {
            max-height: 265px; object-fit: cover; background: #000;
            border: 1px solid #e5e7eb; border-radius: 6px;
        }
        .wb-panel-head {
            display: flex; justify-content: space-between; align-items: baseline;
            border-bottom: 1px solid #e5e7eb; padding-bottom: 0.3rem; margin-bottom: 0.4rem;
        }
        .wb-h { font-size: 0.86rem; font-weight: 800; letter-spacing: 0.08em;
                color: #111827; text-transform: uppercase; }
        .wb-h .acc { color: #dc2626; }
        .wb-h .dot { color: #dc2626; }
        .wb-meta { font-size: 0.72rem; color: #6b7280; font-family: monospace; }
        .wb-chip {
            display: inline-block; padding: 0.10rem 0.5rem; margin: 0.12rem 0.22rem 0.12rem 0;
            border-radius: 4px; font-size: 0.72rem; font-weight: 600;
            border: 1px solid #d1d5db; color: #374151; background: #f9fafb;
            font-family: monospace;
        }
        .wb-chip.on-amber { border-color: #f59e0b; color: #b45309; background: #fffbeb; }
        .wb-chip.on-red   { border-color: #ef4444; color: #b91c1c; background: #fef2f2; }
        .wb-chip.demo { border-color: #e5e7eb; color: #9ca3af; }
        .wb-clock { font-family: monospace; font-size: 0.9rem; color: #111827; }
        .wb-read { font-family: monospace; font-size: 0.78rem; color: #374151;
                   margin-right: 0.9rem; white-space: nowrap; }
        .wb-read b { color: #111827; }
        .wb-badge-anom {
            background: #fef2f2; color: #dc2626; border: 1px solid #fca5a5;
            border-radius: 3px; padding: 0 0.3rem; font-size: 0.68rem; font-weight: 700;
        }
        .wb-card {
            border: 1px solid #e5e7eb; border-radius: 8px; background: #ffffff;
            padding: 0.6rem 0.8rem; margin-bottom: 0.6rem;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        }
        .wb-card .ref { color: #dc2626; font-family: monospace; font-weight: 700; }
        .wb-card .pct { float: right; color: #111827; font-family: monospace; }
        .wb-card .title { color: #111827; font-weight: 700; margin: 0.15rem 0; }
        .wb-card .foot { color: #6b7280; font-size: 0.72rem; }
        .wb-card .foot b { color: #374151; }
        .wb-status { border: 1px solid #059669; color: #047857; border-radius: 4px;
                     padding: 0.05rem 0.45rem; font-size: 0.7rem; font-weight: 700;
                     font-family: monospace; float: right; margin-left: 0.5rem;
                     background: #ecfdf5; }
        .wb-status.partial { border-color: #d97706; color: #b45309; background: #fffbeb; }
        .wb-phrase {
            display: inline-block; color: #047857; background: #ecfdf5;
            border: 1px solid #a7f3d0; border-radius: 3px; padding: 0 0.35rem;
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


@st.cache_data(show_spinner=False)
def _load_optional_parquet(path_str: str) -> pd.DataFrame:
    from pathlib import Path
    path = Path(path_str)
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()


@st.cache_data(show_spinner=False)
def _load_quality_labels() -> dict:
    from src.encoder.train import load_quality_labels
    return load_quality_labels()


@st.cache_resource(show_spinner="Loading vector store + embedder…")
def _load_retrieval(store_path: str):
    """(store, embedder) for live SOP search; None when no index is built."""
    from pathlib import Path

    from src.retrieval.embeddings import build_embedder
    from src.retrieval.store import VectorStore
    if not Path(store_path).exists():
        return None
    store = VectorStore.load(store_path)
    kind = "hashing" if store.embedder_name == "hashing_fallback" else "bge"
    embedder = build_embedder(kind)
    store.require_embedder(embedder.name)
    return store, embedder


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
        st.session_state.pop("wb_jump_pills", None)
        st.session_state.pop("wb_jump_prev", None)
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


def _on_jump() -> None:
    """Evidence-marker click → seek EVERY view (video, sensor, timeline).

    The pills run in multi-select mode (single-select pills break Streamlit's
    AppTest serializer when nothing is selected); the callback reduces the
    selection to the newest pick so it behaves as single-select.
    """
    picked = list(st.session_state.get("wb_jump_pills") or [])
    previous = list(st.session_state.get("wb_jump_prev") or [])
    fresh = [p for p in picked if p not in previous] or picked
    if not fresh:
        st.session_state.wb_jump_prev = []
        return
    target = fresh[-1]
    st.session_state.wb_jump_pills = [target]
    st.session_state.wb_jump_prev = [target]
    info = st.session_state.get("wb_jump_map", {}).get(target)
    if not info:
        return
    state = _state()
    state.seek(info["t"])
    state.stop()
    _store(state)
    st.session_state.wb_selected = info["event_id"]


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


@st.cache_data(show_spinner=False)
def _video_src(path_str: str) -> str:
    """Clip source for the video component: a static-file URL, tiny in the
    ForwardMsg. Inline base64 (~190 KB) crossed Streamlit's message-cache
    threshold and the fragment ticks evicted it mid-session ("Cached
    ForwardMsg MISS"); the data URI remains only as a fallback when the
    static folder is not writable."""
    import shutil
    from pathlib import Path
    src = Path(path_str)
    try:
        static_dir = Path(__file__).resolve().parent / "static" / "video"
        static_dir.mkdir(parents=True, exist_ok=True)
        dest = static_dir / src.name
        if not dest.exists() or dest.stat().st_size != src.stat().st_size:
            shutil.copy2(src, dest)
        return f"/app/static/video/{src.name}"
    except OSError:
        return ("data:video/mp4;base64,"
                + base64.b64encode(src.read_bytes()).decode("ascii"))


VIDEO_COMPONENT_HEIGHT = 296

# The clip follows the GLOBAL incident clock: its own timeline is stretched
# proportionally over [t0, t1] (constructed sync, I-8). JS mirrors the tested
# video_sync_spec() formula, preferring the element's real duration; "rate"
# mode plays natively at clip_rate, otherwise a timer scrubs currentTime.
_VIDEO_HTML = """
<div style="font-family:ui-monospace,monospace;">
  <video id="wbv" muted playsinline preload="auto"
         style="width:100%;height:246px;object-fit:contain;background:#0f172a;
                border-radius:8px;display:block;">
    <source src="__SRC__" type="video/mp4">
  </video>
  <div style="display:flex;align-items:center;gap:8px;margin-top:6px;">
    <div style="flex:1;height:6px;background:#e5e7eb;border-radius:3px;">
      <div id="wbv-bar" style="height:100%;width:0%;background:#0891b2;
           border-radius:3px;"></div>
    </div>
    <span id="wbv-clock" style="font-size:12px;font-weight:600;color:#0e7490;
          white-space:nowrap;">--</span>
  </div>
</div>
<script>
(function() {
  const S = __SPEC__;
  const v = document.getElementById("wbv");
  const bar = document.getElementById("wbv-bar");
  const clock = document.getElementById("wbv-clock");
  const span = Math.max(S.t1 - S.t0, 1e-9);
  const renderStart = performance.now();

  function globalT() {
    if (!S.playing) return S.current_s;
    return Math.min(S.current_s +
      (performance.now() - renderStart) / 1000 * S.transport_rate, S.t1);
  }
  function clipDuration() {
    return (isFinite(v.duration) && v.duration > 0) ? v.duration
                                                    : S.clip_duration_s;
  }
  function clipTarget(g) {
    const frac = Math.min(Math.max((g - S.t0) / span, 0), 1);
    return Math.min(frac * clipDuration(),
                    Math.max(clipDuration() - 0.05, 0));
  }
  function paint(g) {
    const frac = Math.min(Math.max((g - S.t0) / span, 0), 1);
    bar.style.width = (frac * 100).toFixed(2) + "%";
    clock.textContent = "GLOBAL " + g.toFixed(1) + "s / " + S.t1.toFixed(0) + "s";
  }

  v.addEventListener("loadedmetadata", function() {
    v.currentTime = clipTarget(S.current_s);
    paint(globalT());
    if (!S.playing) return;
    const dur = clipDuration();
    const clipRate = dur / span * S.transport_rate;
    const rateMode = clipRate >= 0.0625 && clipRate <= 16;
    if (rateMode) {
      v.playbackRate = clipRate;
      v.play().catch(function() {});
    }
    const timer = setInterval(function() {
      const g = globalT();
      paint(g);
      const target = clipTarget(g);
      // seek mode scrubs; rate mode only corrects visible drift.
      if (!rateMode || Math.abs(v.currentTime - target) > 0.3) {
        v.currentTime = target;
      }
      if (g >= S.t1) { v.pause(); clearInterval(timer); }
    }, 100);
  });
})();
</script>
"""


def _video_component_html(src_url: str, spec) -> str:
    return (_VIDEO_HTML
            .replace("__SRC__", src_url)
            .replace("__SPEC__", json.dumps(asdict(spec))))


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
        spec = video_sync_spec(state, clip_duration)
        components.html(_video_component_html(_video_src(str(video_path)), spec),
                        height=VIDEO_COMPONENT_HEIGHT)
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
        # Keep the transport slider synced to the shared clock on every full
        # rerun (fragment ticks advance the clock without re-instantiating it).
        st.session_state.wb_slider = float(min(max(state.current_time_s,
                                                   state.t0), state.t1))
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


def _render_decoder_report(report: dict) -> None:
    mode_cls = "" if report["mode"] == "llm" else "demo"
    mode_txt = ("REAL LLM (GBNF-constrained)" if report["mode"] == "llm"
                else "MOCK template (deterministic baseline)")
    st.markdown(
        f'<span class="wb-chip {mode_cls}">{mode_txt} · {report["provider"]} · '
        f'{report["latency_s"]:.1f}s</span>'
        f'<span class="wb-chip">confidence {report["confidence"]}</span>',
        unsafe_allow_html=True)
    st.markdown(f"**Failure hypothesis:** {report['failure_hypothesis']}")
    st.markdown("**Chronology:**")
    for i, claim in enumerate(report["chronology"], start=1):
        ids = ", ".join(claim["evidence_ids"])
        st.markdown(f"{i}. [{claim['t_start']:+.1f}s → {claim['t_end']:+.1f}s] "
                    f"{claim['claim']}  \n"
                    f"&nbsp;&nbsp;&nbsp;evidence: `{ids}`")
    if report["sop_links"]:
        st.markdown("**SOP linkage:** " + " · ".join(report["sop_links"]))
    st.markdown("**Corrective actions:** "
                + "; ".join(report["corrective_actions"]))
    if report["uncertainties"]:
        st.caption("Uncertainties: " + "; ".join(report["uncertainties"]))
    if report["unsupported_claims"]:
        st.warning("Guardrails dropped unsupported claims (I-2):\n\n- "
                   + "\n- ".join(report["unsupported_claims"]))


def _render_evidence_panel(incident: pd.Series, linked_cards: list[dict],
                           events, state: PlaybackState, retrieval,
                           grounded_sentences: list[dict],
                           decoder_report: dict | None = None) -> None:
    _panel_head("SOP EVIDENCE &", "EXPLANATION")
    sop_tab, ai_tab, claims_tab = st.tabs(["SOP Evidence", "AI Explanation",
                                           "Claim Verification"])
    with sop_tab:
        box = st.container(height=400, border=False)
        with box:
            if retrieval is not None:
                store, embedder = retrieval
                query = st.text_input(
                    "Live retrieval (real vector search)",
                    value=default_retrieval_query(incident),
                    key=f"wb_sop_query_{incident.get('incident_id', '')}")
                if query.strip():
                    hits = store.search(embedder.embed([query], queries=True)[0], k=4)
                    st.caption(f"top {len(hits)} of {len(store)} chunks · "
                               f"embedder: {store.embedder_name} · scores are "
                               f"real cosine similarities")
                    _render_sop_cards(live_retrieval_cards(hits, store.embedder_name))
            else:
                st.info("No vector index built — run "
                        "`python -m src.retrieval.build_index` (Phase 5).")
            with st.expander("Chunks linked at dataset build (keyword-topic)"):
                _render_sop_cards(linked_cards)
    with ai_tab:
        if decoder_report is not None:
            _render_decoder_report(decoder_report)
            st.divider()
        if grounded_sentences:
            st.markdown("**Grounded sensor chronology (real, per sub-window):**")
            for sentence in grounded_sentences:
                st.markdown(f"- {sentence['text']} — evidence: "
                            f"`{sentence['evidence'][0]}`")
            st.divider()
        st.markdown("**Narrative (decoder LLM lands in Phase 11):**")
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
              axis=alt.Axis(labelColor="#374151", labelFontWeight="bold",
                            labelFontSize=11, ticks=False, domain=False))
    selected = state.selected_event_id or "__none__"
    bars = alt.Chart(frame).mark_bar(cornerRadius=3, height=18,
                                     stroke=None).encode(
        y=y,
        x=alt.X("t_start:Q", title=None, scale=x_scale,
                axis=alt.Axis(format="~s", labelExpr="datum.value + 's'",
                              labelColor="#6b7280", grid=True, gridColor="#e5e7eb")),
        x2="t_end:Q",
        color=alt.Color("color:N", scale=None),
        opacity=alt.condition(alt.datum.active, alt.value(0.50), alt.value(0.22)),
        tooltip=["display_label:N", "t_start:Q", "t_end:Q", "source:N", "detail:N"],
    )
    outlines = alt.Chart(frame).mark_bar(cornerRadius=3, height=18,
                                         filled=False, strokeWidth=1.4).encode(
        y=y, x=alt.X("t_start:Q", scale=x_scale), x2="t_end:Q",
        stroke=alt.Color("color:N", scale=None),
        strokeWidth=alt.condition(f"datum.event_id === '{selected}'",
                                  alt.value(2.8), alt.value(1.4)),
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

    st.title("CNC Incident Workbench")

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

    # ---- real pipeline artifacts (Phases 2-5) ----
    features = _load_optional_parquet(f"{processed_dir}/sensor_features.parquet")
    hvib = _load_optional_parquet(f"{processed_dir}/hvib.parquet")
    quality = _load_quality_labels()
    retrieval = _load_retrieval(f"{processed_dir}/vector_store.parquet")
    split = str(incident.get("split", "unknown"))
    feature_rows = (pd.DataFrame() if is_demo
                    else incident_feature_rows(features, selected, hvib))

    tuples = _load_optional_parquet(f"{processed_dir}/aligned_tuples.parquet")
    tuple_rows = (pd.DataFrame() if is_demo
                  else incident_tuples(tuples, selected))
    video_summaries = _load_optional_parquet(f"{processed_dir}/video_summaries.parquet")
    clip_summary = (None if is_demo else
                    video_summary_for(video_summaries, incident.get("video_file")))

    events = build_timeline_events(incident, t0, t1, rel_offset=rel_offset,
                                   user_notes=_user_notes())
    if clip_summary is not None:
        # Real VLM/tags summary replaces the demo VIDEO bars (Phase 7).
        events = [e for e in events if e.row != "VIDEO"] \
            + vlm_video_events(clip_summary, t0, t1)
    if not tuple_rows.empty:
        # Real grounding replaces the demo SOP bars (Phase 6).
        grounded = grounded_sop_events(tuple_rows, rel_offset, t0, t1)
        if grounded:
            events = [e for e in events if e.row != "SOP"] + grounded
    if not feature_rows.empty:
        events = events + important_interval_events(feature_rows, rel_offset, t0, t1)
    if is_demo:
        cards = build_sop_cards(incident, pd.DataFrame(), pd.DataFrame())
    else:
        sop_chunks, maint_chunks = incident_text_evidence(incident, tables.text_chunks)
        cards = build_sop_cards(incident, sop_chunks, maint_chunks)
    explanation = build_ai_explanation(incident, events)
    claims = build_claim_rows(events)

    # ---- real-status chips (Phase 4 artifacts; test split stays quarantined) ----
    if not is_demo:
        enc = encoder_summary(feature_rows, split)
        qual = quality_chip(quality, selected, split)
        enc_cls = {"ok": "", "quarantined": "demo", "missing": "demo"}[enc["status"]]
        qual_cls = {"good": "", "bad": "on-red",
                    "quarantined": "demo", "missing": "demo"}[qual["status"]]
        st.markdown(
            f'<span class="wb-chip {qual_cls}">{qual["text"]}</span>'
            f'<span class="wb-chip {enc_cls}">{enc["text"]}</span>'
            f'<span class="wb-chip">Sub-windows: {len(feature_rows)}</span>'
            f'<span class="wb-chip">Split: {split}</span>',
            unsafe_allow_html=True)

    # ---- main grid ----
    video_col, sensor_col, evidence_col = st.columns([0.30, 0.38, 0.32], gap="small")
    with video_col, st.container(border=True, height=PANEL_HEIGHT):
        _render_video_panel(incident, state, events, tables.video_index, is_demo)
        if clip_summary is not None:
            mode_chip = ("" if clip_summary["mode"] == "vlm" else "demo")
            st.markdown(
                f'<span class="wb-chip {mode_chip}">'
                f'{clip_summary["mode"].upper()} · {clip_summary["model"]} · '
                f'conf {clip_summary["confidence"]:.2f}</span> '
                + " ".join(f'<span class="wb-chip">{lab}</span>'
                           for lab in clip_summary["labels"][:4]),
                unsafe_allow_html=True)
            st.caption(clip_summary["summary"])
        state = _state()  # transport may have mutated the shared clock
    grounded_sentences = grounded_explanation(tuple_rows) if not tuple_rows.empty else []
    explanations = _load_optional_parquet(f"{processed_dir}/explanations.parquet")
    decoder_report = (None if is_demo
                      else incident_explanation(explanations, selected))
    with evidence_col, st.container(border=True, height=PANEL_HEIGHT):
        _render_evidence_panel(incident, cards, events, state, retrieval,
                               grounded_sentences, decoder_report)
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
                if not live.is_playing:
                    # Play-through reached the final tick: settle the whole
                    # page (transport buttons, video element) into stopped
                    # state at t1 so every view agrees.
                    st.rerun(scope="app")
            if subset.empty:
                st.info("Select at least one channel.")
                return
            readouts = live_readouts(subset, live.current_time_s)
            st.altair_chart(_sensor_chart(subset, events, live, readouts),
                            width="stretch")
            _render_readouts(readouts, live.current_time_s)

        _sensor_live()

        if not feature_rows.empty:
            with st.expander(f"Sub-window features · {len(feature_rows)} windows "
                             f"(real, Phases 2-4)"):
                show = feature_rows.copy()
                show["anomaly_encoder"] = show["anomaly_encoder"].map(
                    lambda v: "quarantined (I-4)" if split == "test"
                    else ("—" if pd.isna(v) else f"{v:.3f}"))
                st.dataframe(show.round(4), hide_index=True, width="stretch")

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

    jump_options = evidence_jump_options(events)
    if jump_options:
        jump_map = {o["event_id"]: o for o in jump_options}
        st.session_state.wb_jump_map = jump_map
        st.pills("Jump to evidence",
                 options=list(jump_map),
                 format_func=lambda i, m=jump_map: m[i]["display"],
                 key="wb_jump_pills", on_change=_on_jump,
                 selection_mode="multi", label_visibility="collapsed")

    @st.fragment(run_every=TICK_SECONDS)
    def _timeline_live() -> None:
        live = _state()
        st.altair_chart(_timeline_chart(events_frame(events, live.current_time_s),
                                        live), width="stretch")

    _timeline_live()

    # ---- evidence selection (fusion v1, Build-A) ----
    bundles = _load_optional_parquet(f"{processed_dir}/evidence_bundles.parquet")
    contexts = _load_optional_parquet(f"{processed_dir}/decoder_contexts.parquet")
    bundle_rows = (pd.DataFrame() if is_demo
                   else incident_bundle(bundles, selected))
    if not bundle_rows.empty:
        with st.expander(f"Evidence selection · fusion v1 · "
                         f"{len(bundle_rows)} ranked items (real scores; feeds "
                         f"the Build-B decoder)"):
            st.dataframe(
                bundle_rows[["modality", "rank", "evidence_id", "score",
                             "confidence", "label", "detail"]].round(4),
                hide_index=True, width="stretch")
            ctx = contexts[contexts["incident_id"] == selected] \
                if not contexts.empty else pd.DataFrame()
            if not ctx.empty:
                st.markdown("**Decoder context (exact Build-B input):**")
                st.code(str(ctx.iloc[0]["context_text"]), language="text")

    # ---- temporal grounding (real aligned tuples, Phase 6) ----
    if not tuple_rows.empty:
        with st.expander(f"Temporal grounding · {len(tuple_rows)} aligned tuples "
                         f"(real, contract-valid, evidence IDs resolve in the "
                         f"evidence graph)"):
            show = tuple_rows[["window_id", "t_start", "t_end", "alarm_state",
                               "sensor_summary", "retrieved_citation",
                               "retrieved_score", "evidence_ids"]].copy()
            st.dataframe(show.round(4), hide_index=True, width="stretch")
            st.caption("sensor_summary and spans are real (Phases 2-4); "
                       "retrieved_citation is real vector retrieval (Phases 5-6) "
                       "grounded by window-context association; video sync "
                       "remains constructed (I-8).")

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
