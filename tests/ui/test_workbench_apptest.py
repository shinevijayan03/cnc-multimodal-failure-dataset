"""In-process render tests for the workbench UI via streamlit.testing.AppTest.

These run the real streamlit_app.py against the locally staged processed data
(no browser needed). Skipped when no build artifacts are staged.
"""

from __future__ import annotations

from pathlib import Path

import pytest

INCIDENTS = Path("data_pipeline/data_processed/incidents.parquet")

pytestmark = pytest.mark.skipif(
    not INCIDENTS.exists(),
    reason="processed incidents not staged; run the pipeline first",
)


def _app():
    from streamlit.testing.v1 import AppTest
    return AppTest.from_file("streamlit_app.py", default_timeout=60)


def _button(at, label_part: str):
    return next(b for b in at.button if label_part in (b.label or ""))


def test_workbench_renders_without_exception():
    at = _app().run()
    assert not at.exception
    # Incident selector present and populated (regression: data still loads).
    selector = next(s for s in at.selectbox if s.key == "main_incident_selector")
    assert selector.value
    # Shared playback state initialized from the sensor axis.
    assert at.session_state["wb_t1"] > at.session_state["wb_t0"]
    assert at.session_state["wb_playing"] is False


def test_play_then_stop_toggles_shared_state():
    at = _app().run()
    _button(at, "Play-through").click()
    at.run()
    assert not at.exception
    assert at.session_state["wb_playing"] is True
    _button(at, "Stop").click()
    at.run()
    assert at.session_state["wb_playing"] is False


def test_scrub_slider_seeks_shared_cursor():
    at = _app().run()
    t0 = at.session_state["wb_t0"]
    t1 = at.session_state["wb_t1"]
    target = (t0 + t1) / 2.0
    slider = next(s for s in at.slider if s.key == "wb_slider")
    slider.set_value(target)
    at.run()
    assert not at.exception
    assert at.session_state["wb_current"] == pytest.approx(target, abs=0.2)
    assert at.session_state["wb_playing"] is False   # scrubbing pauses playback
