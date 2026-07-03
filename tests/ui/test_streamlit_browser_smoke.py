"""Opt-in browser smoke test for the Streamlit incident explorer."""

from __future__ import annotations

import os

import pytest


@pytest.mark.browser
def test_streamlit_incident_explorer_browser_smoke():
    if os.environ.get("RUN_BROWSER_SMOKE") != "1":
        pytest.skip("set RUN_BROWSER_SMOKE=1 when Streamlit is running on localhost:8501")

    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    url = os.environ.get("STREAMLIT_URL", "http://localhost:8501")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        assert page.get_by_text("Recipe A Incident Explorer").first.is_visible()
        assert page.get_by_text("Choose an incident").first.is_visible()
        assert page.get_by_text("Evidence").first.is_visible()
        assert page.get_by_text("Alignment").first.is_visible()
        browser.close()
