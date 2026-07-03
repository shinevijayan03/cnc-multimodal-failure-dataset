"""Streamlit incident explorer for the Recipe A dataset pipeline."""

from __future__ import annotations

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


st.set_page_config(
    page_title="Recipe A Incident Explorer",
    page_icon="",
    layout="wide",
)


def _apply_layout_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1680px;
            padding-top: 1.25rem;
            padding-bottom: 2rem;
        }
        .stApp h1 {
            font-size: 2.35rem;
            line-height: 1.15;
            margin-bottom: 0.35rem;
        }
        div[data-testid="stVideo"] {
            max-width: 100%;
        }
        div[data-testid="stVideo"] video {
            max-height: 310px;
            object-fit: contain;
            background: #101828;
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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


def _render_chunk_group(
    title: str,
    chunks: pd.DataFrame,
    *,
    first_expanded: bool = True,
) -> None:
    st.markdown(f"#### {title}")
    if chunks.empty:
        st.info("No linked chunks for this evidence type.")
        return
    for i, (_, chunk) in enumerate(chunks.iterrows(), start=1):
        tags = decode_list_cell(chunk.get("topic_tags"))
        chunk_id = chunk["chunk_id"]
        doc_type = chunk.get("doc_type", "unknown")
        n_tokens = chunk.get("n_tokens", 0)
        label = f"{i}. {chunk_id} · {doc_type} · {n_tokens} tokens"
        with st.expander(label, expanded=first_expanded and i == 1):
            if tags:
                st.caption("Topics: " + ", ".join(str(tag) for tag in tags))
            st.write(str(chunk.get("text", "")).strip())


def _metric_row(incident: pd.Series) -> None:
    duration = float(incident["window_end_s"]) - float(incident["window_start_s"])
    summary = [
        f"Failure: {incident.get('failure_family', 'unknown')}",
        f"Severity: {incident.get('severity_label', 'unknown')}",
        f"Regime: {incident.get('regime_label', 'unknown')}",
        f"Split: {incident.get('split', 'unknown')}",
        f"fs Hz: {float(incident.get('fs_hz', 0.0)):.0f}",
        f"Window: {duration:.2f}s",
    ]
    st.caption(" | ".join(str(item) for item in summary))


def _render_sensor_evidence(incident: pd.Series, incident_id: str, max_points: int) -> None:
    _sensor_path, sensor_df = _load_sensor(str(incident["sensor_file"]))
    st.markdown("### Vibration")

    channels = available_sensor_channels(sensor_df)
    chosen_channels = st.multiselect(
        "Channels",
        options=channels,
        default=channels[:3],
        key=f"sensor_channels_{incident_id}",
    )
    chart_frame = sensor_plot_frame(sensor_df, chosen_channels, max_points=max_points)
    if chart_frame.empty or not chosen_channels:
        st.info("No numeric sensor channels available for plotting.")
    else:
        st.line_chart(chart_frame, height=320)


def _render_video_evidence(incident: pd.Series) -> None:
    st.markdown("### Video")
    video_path = video_path_for_display(incident, repo_root())
    if video_path is None:
        st.info("This incident has no linked video.")
    elif not video_path.exists():
        st.error(f"Video file is referenced but missing: {video_path}")
    else:
        st.video(str(video_path), width="stretch")


def _render_sop_evidence(incident: pd.Series, text_chunks: pd.DataFrame) -> None:
    st.markdown("### SOP Text")
    sop_chunks, _ = incident_text_evidence(incident, text_chunks)
    text_panel = st.container(height=430, border=False)
    with text_panel:
        _render_chunk_group("SOP Evidence", sop_chunks, first_expanded=True)


def _render_evidence_window(
    incident: pd.Series,
    incident_id: str,
    text_chunks: pd.DataFrame,
    max_points: int,
) -> None:
    video_col, sensor_col, sop_col = st.columns(
        [0.31, 0.35, 0.34],
        gap="medium",
        vertical_alignment="top",
    )
    with video_col:
        with st.container(border=True, height=520):
            _render_video_evidence(incident)
    with sensor_col:
        with st.container(border=True, height=520):
            _render_sensor_evidence(incident, incident_id, max_points)
    with sop_col:
        with st.container(border=True, height=520):
            _render_sop_evidence(incident, text_chunks)


def main() -> None:
    _apply_layout_styles()
    st.title("Recipe A Incident Explorer")

    with st.sidebar:
        st.header("Dataset")
        processed_dir = st.text_input(
            "Processed data folder",
            value=DEFAULT_PROCESSED_DIR.as_posix(),
        )
        if st.button("Refresh data", width="stretch"):
            st.cache_data.clear()
        st.caption("Rerun the ETL, then refresh to see new incidents.")

        status = _artifact_status(processed_dir)
        st.dataframe(status, hide_index=True, width="stretch")

    tables = _load_tables(processed_dir)
    incidents = tables.incidents

    if incidents.empty:
        st.error("No incidents.parquet found. Run the pipeline first.")
        st.code("python -m src.cli all --config config/dataset.yaml", language="bash")
        return

    labels = incident_labels(incidents)
    incident_ids = list(labels.keys())

    control_cols = st.columns([0.7, 0.3], gap="large", vertical_alignment="bottom")
    with control_cols[0]:
        selected = st.selectbox(
            "Choose an incident",
            options=incident_ids,
            format_func=lambda inc_id: labels.get(inc_id, inc_id),
            key="main_incident_selector",
        )
    with control_cols[1]:
        max_points = st.slider(
            "Sensor chart max points",
            min_value=500,
            max_value=10000,
            value=3000,
            step=500,
            key="main_sensor_max_points",
        )

    incident = find_incident(incidents, selected)

    st.caption(f"Incident ID: `{selected}`")
    _metric_row(incident)

    evidence_tab, alignment_tab, row_tab = st.tabs([
        "Evidence",
        "Alignment",
        "Raw Row",
    ])

    with evidence_tab:
        _render_evidence_window(incident, selected, tables.text_chunks, max_points)

    with alignment_tab:
        st.subheader("Cross-Modal Alignment Summary")
        st.dataframe(alignment_rows(incident), hide_index=True, width="stretch")
        st.info(
            "The sensor window is the temporal anchor. Video and text are linked by "
            "the current matching/retrieval heuristics and should be treated as "
            "relevant evidence, not physically synchronized ground truth."
        )

    with row_tab:
        st.subheader("Incident Row")
        raw_row = incident.to_frame("value").astype({"value": "string"})
        st.dataframe(raw_row, width="stretch")


if __name__ == "__main__":
    main()
