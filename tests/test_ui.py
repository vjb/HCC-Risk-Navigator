"""
TDD Phase 4 — Playwright UI Tests for Streamlit EHR Dashboard.
Updated for the Enterprise SaaS "HCC Risk Navigator" layout.

Run with:
    pytest tests/test_ui.py -v
"""
from __future__ import annotations

import os
import subprocess
import time

import pytest
from playwright.sync_api import Page, sync_playwright

import sys

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
    env = {**os.environ, "DATABASE_URL": "sqlite:///data/mock_ehr.sqlite"}

    # Initialize and seed
    seed_proc = subprocess.run(
        [sys.executable, "scripts/seed_db.py"],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    assert seed_proc.returncode == 0, f"Seeding failed: {seed_proc.stderr}"

    # Start Streamlit
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", "app.py",
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
# UI Rendering Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEnterpriseDashboard:
    def test_page_title_is_correct(self, browser_page: Page):
        """The page title must explicitly match the HCC project."""
        title = browser_page.title()
        assert "HCC Risk Navigator" in title, f"Expected 'HCC Risk Navigator' in title, got '{title}'"

    def test_cfo_metrics_are_visible(self, browser_page: Page):
        """The macro enterprise metrics (e.g., $510,000) must render at the top."""
        content = browser_page.content()
        assert "Clinic-Wide Value-Based Care" in content, "CFO Header missing"
        assert "$510,000" in content, "Revenue projection metric missing"

    def test_patient_banner_renders_tamara(self, browser_page: Page):
        """Tamara's demographics must be visible in the custom CSS banner."""
        content = browser_page.content()
        assert "Tamara Williams" in content, "Patient name missing"
        assert "Medicare Advantage" in content, "Insurance badge missing"

    def test_coded_problem_list_shows_e11_9(self, browser_page: Page):
        """The active problem list must show her baseline diabetes code."""
        content = browser_page.content()
        assert "E11.9" in content, "Baseline ICD-10 code E11.9 missing from problem list"

    def test_clinical_notes_render(self, browser_page: Page):
        """The unstructured notes containing the evidence must be visible."""
        content = browser_page.content()
        assert "burning sensation" in content.lower(), "HCC gap evidence ('burning sensation') missing from notes"

    def test_audit_button_exists(self, browser_page: Page):
        """The primary call-to-action button must be available."""
        # Playwright checks if the button text exists in the DOM
        button_visible = browser_page.get_by_role("button", name="Execute AI Chart Audit").is_visible()
        # Fallback to content check if Streamlit's shadow DOM hides the role
        if not button_visible:
            assert "Execute AI Chart Audit" in browser_page.content(), "Audit button missing"
