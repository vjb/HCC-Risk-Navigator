"""
TDD Phase 2 — PA Reasoning Engine Tests (written BEFORE implementation).

Tests assert that pa_engine.generate_pa_analysis():
  1. Correctly identifies step-therapy failure (2 months < 6-month requirement).
  2. Correctly finds the GI intolerance clinical exception.
  3. Returns a drafted PA justification letter.
  4. Handles the case where step-therapy IS met (no exception needed).
  5. Returns structured JSON with all expected keys.

The OpenAI LLM call is mocked via pytest-mock — no real API calls.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.pa_engine import generate_pa_analysis, StepTherapyResult


# ─────────────────────────────────────────────────────────────────────────────
# Test Fixtures — Synthetic FHIR-like payload (mirrors what get_fhir_context returns)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def tamara_fhir_context() -> dict:
    """Simulated output of get_fhir_context('tamara-chen-001')."""
    course_start = (date.today() - timedelta(days=120)).isoformat()
    course_end = (date.today() - timedelta(days=59)).isoformat()
    return {
        "patient": {
            "fhir_id": "tamara-chen-001",
            "name": "Tamara Chen",
            "dob": "1978-04-15",
            "gender": "female",
        },
        "medications": [
            {
                "medication_name": "Metformin 500 MG Oral Tablet",
                "start_date": course_start,
                "end_date": course_end,
                "status": "completed",
            }
        ],
        "observations": [
            {"display": "A1C", "loinc_code": "4548-4", "value": 8.1, "unit": "%", "effective_date": course_end},
        ],
        "clinical_notes": [
            {
                "note_type": "Progress Note",
                "content": (
                    "Patient reports severe GI intolerance since initiating Metformin therapy. "
                    "Metformin DISCONTINUED due to severe gastrointestinal adverse effects. "
                    "GI intolerance documented as primary reason for inability to complete "
                    "required step-therapy course."
                ),
                "authored_date": course_end,
            }
        ],
    }


@pytest.fixture()
def aetna_policy_text() -> str:
    return (
        "Aetna Step Therapy Policy for GLP-1 Receptor Agonists (e.g., Ozempic/semaglutide):\n"
        "Requirement: Patient must have an inadequate response or intolerance to at least "
        "6 months of metformin therapy at a maximally tolerated dose.\n"
        "Exception: Step therapy may be bypassed if the patient has a documented "
        "contraindication or clinically significant adverse effect to metformin, including "
        "but not limited to: severe gastrointestinal intolerance, lactic acidosis risk, "
        "or renal impairment."
    )


@pytest.fixture()
def mock_llm_pa_response() -> str:
    """The structured JSON string we expect the mocked LLM to return."""
    return json.dumps({
        "step_therapy_assessment": "FAILED — Patient completed only 61 days of Metformin therapy. Aetna policy requires a minimum of 6 months (approximately 180 days).",
        "exception_found": True,
        "exception_evidence": "Clinical progress note dated [date] documents severe GI intolerance to Metformin (nausea, abdominal cramping, diarrhea) resulting in documented discontinuation. This constitutes a qualifying clinical exception under Aetna policy.",
        "pa_letter": (
            "PRIOR AUTHORIZATION EXCEPTION REQUEST\n\n"
            "To: Aetna Prior Authorization Department\n"
            "Re: Patient Tamara Chen — Ozempic (Semaglutide 0.5mg weekly)\n\n"
            "We are requesting prior authorization exception for Ozempic (semaglutide) "
            "for patient Tamara Chen (DOB: 1978-04-15) with Type 2 Diabetes Mellitus.\n\n"
            "STEP THERAPY STATUS: Patient initiated Metformin 500mg BID on [start_date]. "
            "Therapy was discontinued after 61 days due to severe gastrointestinal adverse "
            "effects. This does not meet the 6-month step therapy requirement.\n\n"
            "CLINICAL EXCEPTION: Per documented clinical note, patient experienced severe "
            "GI intolerance to Metformin, constituting a qualifying exception under Aetna "
            "policy guidelines. Continued Metformin therapy is clinically contraindicated.\n\n"
            "We respectfully request approval of Ozempic as first-line alternative therapy.\n\n"
            "Dr. Sarah Morrison, MD\nBoard Certified — Internal Medicine & Endocrinology"
        ),
    })


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestStepTherapyDetection:
    def test_step_therapy_fails_for_two_month_course(
        self, tamara_fhir_context, aetna_policy_text, mock_llm_pa_response
    ):
        """Two-month Metformin course must NOT satisfy a 6-month requirement."""
        with patch("src.pa_engine._call_llm", return_value=mock_llm_pa_response):
            result = generate_pa_analysis(
                fhir_context=tamara_fhir_context,
                target_medication="Ozempic (semaglutide 0.5mg)",
                policy_text=aetna_policy_text,
            )
        assert result["step_therapy_met"] is False, (
            "Expected step_therapy_met=False for a 61-day course (6 months required)"
        )

    def test_step_therapy_passes_for_six_month_course(
        self, tamara_fhir_context, aetna_policy_text
    ):
        """A 6-month course should be flagged as step therapy met."""
        ctx = tamara_fhir_context.copy()
        ctx["medications"] = [
            {
                "medication_name": "Metformin 500 MG Oral Tablet",
                "start_date": (date.today() - timedelta(days=200)).isoformat(),
                "end_date": (date.today() - timedelta(days=10)).isoformat(),
                "status": "completed",
            }
        ]
        # Suppress LLM for this test — we're testing local logic only
        llm_response = json.dumps({
            "step_therapy_assessment": "MET",
            "exception_found": False,
            "exception_evidence": "",
            "pa_letter": "Prior auth may not be required.",
        })
        with patch("src.pa_engine._call_llm", return_value=llm_response):
            result = generate_pa_analysis(
                fhir_context=ctx,
                target_medication="Ozempic (semaglutide 0.5mg)",
                policy_text=aetna_policy_text,
            )
        assert result["step_therapy_met"] is True


class TestClinicalExceptionDetection:
    def test_gi_intolerance_exception_found(
        self, tamara_fhir_context, aetna_policy_text, mock_llm_pa_response
    ):
        """GI intolerance in clinical notes must trigger exception_found=True."""
        with patch("src.pa_engine._call_llm", return_value=mock_llm_pa_response):
            result = generate_pa_analysis(
                fhir_context=tamara_fhir_context,
                target_medication="Ozempic (semaglutide 0.5mg)",
                policy_text=aetna_policy_text,
            )
        assert result["exception_found"] is True
        assert result["exception_evidence"], "exception_evidence should not be empty"
        # Evidence must mention GI intolerance
        assert any(
            kw in result["exception_evidence"].lower()
            for kw in ("gi", "gastrointestinal", "intolerance", "adverse")
        )

    def test_no_exception_when_notes_are_clean(
        self, tamara_fhir_context, aetna_policy_text
    ):
        """When no exception keywords exist in notes, exception_found should be False."""
        ctx = tamara_fhir_context.copy()
        ctx["clinical_notes"] = [
            {
                "note_type": "Progress Note",
                "content": "Patient tolerating Metformin well. Continue current regimen.",
                "authored_date": date.today().isoformat(),
            }
        ]
        llm_response = json.dumps({
            "step_therapy_assessment": "FAILED",
            "exception_found": False,
            "exception_evidence": "",
            "pa_letter": "No qualifying exception found.",
        })
        with patch("src.pa_engine._call_llm", return_value=llm_response):
            result = generate_pa_analysis(
                fhir_context=ctx,
                target_medication="Ozempic (semaglutide 0.5mg)",
                policy_text=aetna_policy_text,
            )
        assert result["exception_found"] is False


class TestPALetterGeneration:
    def test_pa_letter_is_returned(
        self, tamara_fhir_context, aetna_policy_text, mock_llm_pa_response
    ):
        """PA letter must be a non-empty string."""
        with patch("src.pa_engine._call_llm", return_value=mock_llm_pa_response):
            result = generate_pa_analysis(
                fhir_context=tamara_fhir_context,
                target_medication="Ozempic (semaglutide 0.5mg)",
                policy_text=aetna_policy_text,
            )
        assert isinstance(result["pa_letter"], str)
        assert len(result["pa_letter"]) > 100, "PA letter is suspiciously short"
        assert "Prior Authorization" in result["pa_letter"]

    def test_result_contains_all_required_keys(
        self, tamara_fhir_context, aetna_policy_text, mock_llm_pa_response
    ):
        """Result payload must contain all expected keys."""
        with patch("src.pa_engine._call_llm", return_value=mock_llm_pa_response):
            result = generate_pa_analysis(
                fhir_context=tamara_fhir_context,
                target_medication="Ozempic (semaglutide 0.5mg)",
                policy_text=aetna_policy_text,
            )
        required_keys = {
            "step_therapy_met",
            "exception_found",
            "exception_evidence",
            "pa_letter",
            "therapy_duration_days",
            "required_duration_days",
            "target_medication",
        }
        missing = required_keys - set(result.keys())
        assert not missing, f"Result is missing keys: {missing}"

    def test_therapy_duration_is_accurate(
        self, tamara_fhir_context, aetna_policy_text, mock_llm_pa_response
    ):
        """Returned therapy_duration_days must reflect the actual medication period."""
        with patch("src.pa_engine._call_llm", return_value=mock_llm_pa_response):
            result = generate_pa_analysis(
                fhir_context=tamara_fhir_context,
                target_medication="Ozempic (semaglutide 0.5mg)",
                policy_text=aetna_policy_text,
            )
        assert 50 <= result["therapy_duration_days"] <= 70, (
            f"Expected ~61 days therapy duration, got {result['therapy_duration_days']}"
        )
