"""Opt-in browser smoke test for the CNC incident workbench UI."""

from __future__ import annotations

import os

import pytest


@pytest.mark.browser
def test_incident_workbench_browser_smoke():
    if os.environ.get("RUN_BROWSER_SMOKE") != "1":
        pytest.skip("set RUN_BROWSER_SMOKE=1 when Streamlit is running on localhost:8501")

    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    url = os.environ.get("STREAMLIT_URL", "http://localhost:8501")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        # Header + incident selection (regression: incident page still renders)
        assert page.get_by_text("CNC Incident Workbench").first.is_visible()
        assert page.get_by_text("Choose an incident").first.is_visible()
        # Workbench panels
        assert page.get_by_text("Machine video stream").first.is_visible()
        assert page.get_by_text("Sensor time-series").first.is_visible()
        assert page.get_by_text("Temporal alignment timeline").first.is_visible()
        # Playback controls + export
        assert page.get_by_text("Play-through").first.is_visible()
        assert page.get_by_text("Stop").first.is_visible()
        assert page.get_by_text("Export evidence report").first.is_visible()
        # Evidence tabs
        assert page.get_by_text("SOP Evidence").first.is_visible()
        assert page.get_by_text("AI Explanation").first.is_visible()
        assert page.get_by_text("Claim Verification").first.is_visible()
        browser.close()
