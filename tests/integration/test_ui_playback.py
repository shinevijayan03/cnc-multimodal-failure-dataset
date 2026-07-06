"""IT-UI-CLOCK — one shared global incident clock across all views (Build-C).

Functional tests through Streamlit's AppTest harness on the real app: the
Play-through transport, the fragment tick, Stop, slider seek, and the
end-of-axis settle must all mutate ONE clock (st.session_state.wb_current)
that the video component, sensor chart, and timeline all render from.

The video element itself runs in the browser; its contract with the shared
clock (video_sync_spec) is unit-tested, and here we assert the component HTML
embeds exactly that spec.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from src.ui.workbench import PlaybackState, video_sync_spec

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = Path(__file__).resolve().parents[2] / "streamlit_app.py"
ARTIFACTS = Path("data_pipeline/data_processed/incidents.parquet")

pytestmark = pytest.mark.skipif(
    not ARTIFACTS.exists(),
    reason="pipeline artifacts not built (run the pipeline first)")


@pytest.fixture(scope="module")
def app() -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=180)
    at.run()
    assert not at.exception
    return at


def _button(at: AppTest, label: str):
    hits = [b for b in at.button if b.label == label]
    assert hits, f"button {label!r} not found"
    return hits[0]


def test_play_through_ticks_the_shared_clock(app: AppTest):
    at = app
    t0 = at.session_state["wb_t0"]
    assert at.session_state["wb_current"] == t0
    _button(at, "▷ Play-through").click().run()
    assert at.session_state["wb_playing"] is True
    # Simulate 3 s of wall clock, then let the fragment tick once.
    at.session_state["wb_last_tick"] = time.monotonic() - 3.0
    at.run()
    advanced = at.session_state["wb_current"]
    assert 2.0 < advanced - t0 < 5.0          # one tick advanced ~3 s
    assert at.session_state["wb_playing"] is True


def test_stop_freezes_the_shared_clock(app: AppTest):
    at = app
    _button(at, "⏸ Stop").click().run()
    assert at.session_state["wb_playing"] is False
    frozen = at.session_state["wb_current"]
    at.session_state["wb_last_tick"] = time.monotonic() - 60.0
    at.run()
    assert at.session_state["wb_current"] == frozen   # no tick while stopped


def test_slider_seek_updates_the_shared_clock(app: AppTest):
    at = app
    at.slider(key="wb_slider").set_value(5.0).run()
    assert at.session_state["wb_current"] == pytest.approx(5.0)
    assert at.session_state["wb_playing"] is False
    # The transport slider re-syncs to the clock on the rerun.
    assert at.slider(key="wb_slider").value == pytest.approx(5.0)


def test_play_through_settles_at_the_final_tick(app: AppTest):
    """Target 3: the playhead reaches t1 (the last timeline tick), then stops."""
    at = app
    _button(at, "▷ Play-through").click().run()
    at.session_state["wb_last_tick"] = time.monotonic() - 10_000.0
    at.run()
    assert at.session_state["wb_current"] == at.session_state["wb_t1"]
    assert at.session_state["wb_playing"] is False
    # Replays from t0 after finishing (the fragment may tick a fraction of a
    # second of real wall-clock during the rerun itself).
    _button(at, "▷ Play-through").click().run()
    assert at.session_state["wb_current"] - at.session_state["wb_t0"] < 1.5
    assert at.session_state["wb_playing"] is True
    _button(at, "⏸ Stop").click().run()


def test_evidence_marker_click_seeks_every_view(app: AppTest):
    """Target 5: evidence click updates video, sensor, and timeline together."""
    at = app
    groups = [g for g in at.get("button_group")
              if getattr(g, "key", "") == "wb_jump_pills"]
    assert groups, "evidence jump markers not rendered"
    jump_map = at.session_state["wb_jump_map"]
    # Pick the last (latest) evidence marker so the seek is observable.
    target_id = max(jump_map, key=lambda k: jump_map[k]["t"])
    groups[0].set_value([target_id]).run()
    assert at.session_state["wb_current"] == pytest.approx(
        jump_map[target_id]["t"])
    assert at.session_state["wb_playing"] is False        # click = precise seek
    assert at.session_state["wb_selected"] == target_id
    # The transport slider (video panel) followed the same clock.
    assert at.slider(key="wb_slider").value == pytest.approx(
        jump_map[target_id]["t"])


def test_video_component_embeds_the_shared_clock_spec():
    """The HTML5 video is driven by exactly the unit-tested sync spec."""
    from streamlit_app import _video_component_html

    state = PlaybackState(t0=0.0, t1=16.0, current_time_s=8.0, is_playing=True)
    spec = video_sync_spec(state, clip_duration_s=2.0)
    html = _video_component_html("/app/static/video/vid_x.mp4", spec)
    assert 'src="/app/static/video/vid_x.mp4"' in html
    payload = json.loads(html.split("const S = ", 1)[1].split(";\n", 1)[0])
    assert payload["t1"] == 16.0 and payload["playing"] is True
    assert payload["clip_rate"] == pytest.approx(0.125)
    assert payload["drive_mode"] == "rate"
    assert payload["current_s"] == 8.0


def test_video_src_is_a_small_static_url_not_inline_base64():
    """Inline base64 caused "Cached ForwardMsg MISS" (message-cache eviction
    under fragment ticks); the component must reference a static URL."""
    from src.ui.incident_explorer import repo_root
    from streamlit_app import _video_src

    videos = sorted((repo_root() / "data_pipeline" / "data_processed"
                     / "video").glob("*.mp4"))
    assert videos, "no processed clips available"
    src = _video_src.__wrapped__(str(videos[0]))     # bypass st.cache_data
    assert src == f"/app/static/video/{videos[0].name}"
    copied = repo_root() / "static" / "video" / videos[0].name
    assert copied.exists()
    assert copied.stat().st_size == videos[0].stat().st_size
    assert len(src) < 200                            # tiny ForwardMsg payload
