"""
TDD Phase 4 — Playwright UI Tests for Streamlit EHR Dashboard.
Written BEFORE the Streamlit app is implemented.

These tests launch the Streamlit app in a subprocess and verify the
rendered content via a headless browser.

Run with:
    playwright install chromium
    pytest tests/test_ui.py -v
"""
from __future__ import annotations

import os
import subprocess
import time

import pytest
from playwright.sync_api import Page, expect, sync_playwright

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures — Streamlit subprocess management
# ─────────────────────────────────────────────────────────────────────────────

STREAMLIT_PORT = 8502  # Use non-default port to avoid conflicts with dev server
STREAMLIT_URL = f"http://localhost:{STREAMLIT_PORT}"


@pytest.fixture(scope="module")
def streamlit_server():
    """
    Start Streamlit in a subprocess for the test session.
    Ensures the db is seeded before launching.
    """
    # Seed the database first
    env = {**os.environ, "DATABASE_URL": "sqlite:///data/mock_ehr.sqlite"}

    # Initialize and seed
    seed_proc = subprocess.run(
        ["python", "scripts/seed_db.py"],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    assert seed_proc.returncode == 0, f"Seeding failed: {seed_proc.stderr}"

    # Start Streamlit
    proc = subprocess.Popen(
        [
            "python", "-m", "streamlit", "run", "app.py",
            "--server.port", str(STREAMLIT_PORT),
            "--server.headless", "true",
            "--server.runOnSave", "false",
            "--browser.gatherUsageStats", "false",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for Streamlit to be ready
    time.sleep(8)
    yield proc

    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture(scope="module")
def browser_page(streamlit_server):
    """Provide a Playwright page connected to the running Streamlit app."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(STREAMLIT_URL, wait_until="networkidle", timeout=30000)
        # Wait for Streamlit to fully render
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        yield page
        browser.close()


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDashboardLoads:
    def test_page_title_contains_app_name(self, browser_page: Page):
        """The page title must reference the EHR dashboard."""
        title = browser_page.title()
        assert "Auto-Auth" in title or "Prior Auth" in title or "EHR" in title, (
            f"Page title '{title}' does not reference the app"
        )

    def test_patient_name_tamara_visible(self, browser_page: Page):
        """Patient name 'Tamara' must appear on the dashboard."""
        content = browser_page.content()
        assert "Tamara" in content, "Patient name 'Tamara' not found on dashboard"

    def test_medications_section_visible(self, browser_page: Page):
        """The medications section must be visible."""
        content = browser_page.content()
        assert "Metformin" in content or "Medication" in content, (
            "No medication content found on dashboard"
        )

    def test_clinical_notes_section_visible(self, browser_page: Page):
        """Clinical notes section must be visible."""
        content = browser_page.content()
        assert "GI intolerance" in content or "Clinical Note" in content or "Progress Note" in content, (
            "No clinical notes content found on dashboard"
        )

    def test_a1c_data_visible(self, browser_page: Page):
        """A1C lab data must appear somewhere on the dashboard."""
        content = browser_page.content()
        assert "A1C" in content or "A1c" in content or "Hemoglobin" in content, (
            "No A1C/lab data found on dashboard"
        )


class TestDashboardNavigation:
    def test_tabs_or_sections_present(self, browser_page: Page):
        """Dashboard must have navigation elements (tabs, sidebar, or section headers)."""
        content = browser_page.content()
        # Check for any of: tabs, sections, or sidebar nav links
        assert any(
            kw in content for kw in ["tab", "Tab", "sidebar", "Sidebar", "Medications", "Observations"]
        ), "No navigation elements found"
