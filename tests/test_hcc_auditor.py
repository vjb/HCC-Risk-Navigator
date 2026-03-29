"""
TDD Phase 2 — HCC Auditor Engine Tests (written BEFORE implementation).

Tests assert that audit_hcc_gaps():
  1. Correctly computes current RAF from coded conditions.
  2. Identifies E11.40 as a gap when "burning feet" is in the note.
  3. Returns evidence_quote from the actual note text.
  4. Projects a higher RAF after gap capture.
  5. Returns all required output keys.
  6. Handles a patient with zero HCC gaps gracefully.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from src.hcc_engine import audit_hcc_gaps, compute_raf, HCC_MAP


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def tamara_fhir_context() -> dict:
    """Simulates the output of get_fhir_context('tamara-williams-001')."""
    return {
        "patient": {
            "fhir_id": "tamara-williams-001",
            "name": "Tamara Williams",
            "dob": "1956-03-12",
            "gender": "female",
            "insurance_plan": "Medicare Advantage",
        },
        "conditions": [
            {
                "icd10_code": "E11.9",
                "description": "Type 2 diabetes mellitus without complications",
                "hcc_code": 19,
                "raf_weight": 0.104,
                "clinical_status": "active",
            }
        ],
        "clinical_notes": [
            {
                "note_type": "Office Visit Note",
                "authored_date": (date.today() - timedelta(days=14)).isoformat(),
                "content": (
                    "Patient is a 68-year-old female with known Type 2 diabetes presenting "
                    "for routine follow-up. Patient complains of worsening numbness and a "
                    "burning sensation in both feet over the last 3 months. Bilateral lower "
                    "extremity involved. Symptoms consistent with peripheral neuropathy. "
                    "Gabapentin 300mg TID prescribed for symptom management. "
                    "Patient to follow up in 6 weeks."
                ),
            }
        ],
    }


@pytest.fixture()
def mock_llm_gap_response() -> str:
    """Simulated LLM response identifying the E11.40 gap."""
    return json.dumps({
        "gaps": [
            {
                "suspected_icd10": "E11.40",
                "suspected_hcc": 18,
                "description": "Type 2 diabetes mellitus with diabetic neuropathy, unspecified",
                "evidence_quote": "worsening numbness and a burning sensation in both feet over the last 3 months",
                "clinical_rationale": (
                    "The clinical documentation describes bilateral lower extremity numbness "
                    "and burning consistent with diabetic peripheral neuropathy. Gabapentin "
                    "prescription further supports this diagnosis. Code E11.40 is appropriate."
                ),
                "raf_delta": 0.302,
                "confidence": "HIGH",
            }
        ],
        "audit_summary": (
            "One HCC coding gap identified. The clinical note documents symptoms of "
            "diabetic peripheral neuropathy (burning feet, numbness) with Gabapentin "
            "prescribed, but E11.40 is absent from the problem list. Recommend adding "
            "E11.40 to accurately reflect HCC 18 and increase RAF from 0.104 to 0.302."
        ),
    })


@pytest.fixture()
def mock_llm_no_gaps_response() -> str:
    """Simulated LLM response with no gaps found."""
    return json.dumps({
        "gaps": [],
        "audit_summary": "No HCC coding gaps identified. The problem list appears complete.",
    })


# ─────────────────────────────────────────────────────────────────────────────
# compute_raf() unit tests — no LLM needed
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeRAF:
    def test_single_hcc_code(self):
        """E11.9 alone should yield RAF 0.104."""
        result = compute_raf(["E11.9"])
        assert abs(result - 0.104) < 0.001

    def test_multiple_hcc_codes(self):
        """E11.9 + I50.9 should sum their RAFs."""
        result = compute_raf(["E11.9", "I50.9"])
        expected = 0.104 + 0.331
        assert abs(result - expected) < 0.001

    def test_no_duplicate_hcc_codes(self):
        """E11.9 and E11.65 both map to different HCCs, both should be counted."""
        # E11.9 = HCC 19 (RAF 0.104), E11.65 = HCC 18 (RAF 0.302) — different HCCs
        result = compute_raf(["E11.9", "E11.65"])
        expected = 0.104 + 0.302
        assert abs(result - expected) < 0.001

    def test_non_hcc_code_excluded(self):
        """I10 (hypertension) has HCC 0 and should not add to RAF."""
        result = compute_raf(["I10"])
        assert result == 0.0

    def test_empty_code_list(self):
        assert compute_raf([]) == 0.0

    def test_unknown_code_ignored(self):
        assert compute_raf(["Z99.99Z"]) == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# audit_hcc_gaps() — with mocked LLM
# ─────────────────────────────────────────────────────────────────────────────

class TestHCCGapDetection:
    def test_gap_found_for_burning_feet_note(self, tamara_fhir_context, mock_llm_gap_response):
        """The engine must identify E11.40 as a gap from the burning feet note."""
        with patch("src.hcc_engine._call_llm", return_value=mock_llm_gap_response):
            result = audit_hcc_gaps(tamara_fhir_context)
        assert result["gap_count"] >= 1
        gap_codes = [g["suspected_icd10"] for g in result["gaps"]]
        assert "E11.40" in gap_codes, f"Expected E11.40 in gaps, got {gap_codes}"

    def test_evidence_quote_is_returned(self, tamara_fhir_context, mock_llm_gap_response):
        """Each gap must have a non-empty evidence_quote from the note."""
        with patch("src.hcc_engine._call_llm", return_value=mock_llm_gap_response):
            result = audit_hcc_gaps(tamara_fhir_context)
        for gap in result["gaps"]:
            assert gap["evidence_quote"], f"Gap {gap['suspected_icd10']} has no evidence_quote"

    def test_confidence_level_present(self, tamara_fhir_context, mock_llm_gap_response):
        """Each gap must have a confidence level (HIGH/MEDIUM/LOW)."""
        with patch("src.hcc_engine._call_llm", return_value=mock_llm_gap_response):
            result = audit_hcc_gaps(tamara_fhir_context)
        for gap in result["gaps"]:
            assert gap["confidence"] in ("HIGH", "MEDIUM", "LOW")

    def test_no_gaps_returns_empty_list(self, tamara_fhir_context, mock_llm_no_gaps_response):
        """When no gaps are found, gaps must be an empty list — not None or missing."""
        with patch("src.hcc_engine._call_llm", return_value=mock_llm_no_gaps_response):
            result = audit_hcc_gaps(tamara_fhir_context)
        assert result["gaps"] == []
        assert result["gap_count"] == 0


class TestRAFProjection:
    def test_current_raf_is_0_104(self, tamara_fhir_context, mock_llm_gap_response):
        """Tamara's current RAF (E11.9 only) must be 0.104."""
        with patch("src.hcc_engine._call_llm", return_value=mock_llm_gap_response):
            result = audit_hcc_gaps(tamara_fhir_context)
        assert abs(result["current_raf"] - 0.104) < 0.001, (
            f"Expected current_raf=0.104, got {result['current_raf']}"
        )

    def test_projected_raf_is_higher_after_gap_capture(self, tamara_fhir_context, mock_llm_gap_response):
        """Projected RAF must be higher than current RAF when gaps are found."""
        with patch("src.hcc_engine._call_llm", return_value=mock_llm_gap_response):
            result = audit_hcc_gaps(tamara_fhir_context)
        assert result["projected_raf"] > result["current_raf"], (
            f"Projected RAF ({result['projected_raf']}) must exceed current RAF ({result['current_raf']})"
        )

    def test_e11_40_adds_correct_raf_delta(self, tamara_fhir_context, mock_llm_gap_response):
        """Adding E11.40 (HCC 18) should bring RAF to 0.302 (replaces HCC 19 with HCC 18)."""
        with patch("src.hcc_engine._call_llm", return_value=mock_llm_gap_response):
            result = audit_hcc_gaps(tamara_fhir_context)
        # E11.40 is HCC 18 (RAF 0.302) — different from current HCC 19 (RAF 0.104)
        assert result["projected_raf"] >= 0.302, (
            f"Expected projected_raf ≥ 0.302, got {result['projected_raf']}"
        )

    def test_raf_delta_is_positive(self, tamara_fhir_context, mock_llm_gap_response):
        """RAF delta must be positive when coding gaps are found."""
        with patch("src.hcc_engine._call_llm", return_value=mock_llm_gap_response):
            result = audit_hcc_gaps(tamara_fhir_context)
        assert result["raf_delta"] > 0

    def test_raf_delta_is_zero_when_no_gaps(self, tamara_fhir_context, mock_llm_no_gaps_response):
        """RAF delta must be 0.0 when no gaps are found."""
        with patch("src.hcc_engine._call_llm", return_value=mock_llm_no_gaps_response):
            result = audit_hcc_gaps(tamara_fhir_context)
        assert result["raf_delta"] == 0.0


class TestOutputStructure:
    def test_all_required_keys_present(self, tamara_fhir_context, mock_llm_gap_response):
        """Audit result must have all required top-level keys."""
        with patch("src.hcc_engine._call_llm", return_value=mock_llm_gap_response):
            result = audit_hcc_gaps(tamara_fhir_context)
        required = {
            "patient_id", "patient_name", "current_raf", "projected_raf",
            "raf_delta", "existing_codes", "gaps", "audit_summary", "gap_count",
        }
        missing = required - set(result.keys())
        assert not missing, f"Missing keys: {missing}"

    def test_patient_name_is_tamara(self, tamara_fhir_context, mock_llm_gap_response):
        with patch("src.hcc_engine._call_llm", return_value=mock_llm_gap_response):
            result = audit_hcc_gaps(tamara_fhir_context)
        assert "Tamara" in result["patient_name"]

    def test_existing_codes_contains_e11_9(self, tamara_fhir_context, mock_llm_gap_response):
        with patch("src.hcc_engine._call_llm", return_value=mock_llm_gap_response):
            result = audit_hcc_gaps(tamara_fhir_context)
        assert "E11.9" in result["existing_codes"]

    def test_audit_summary_is_non_empty_string(self, tamara_fhir_context, mock_llm_gap_response):
        with patch("src.hcc_engine._call_llm", return_value=mock_llm_gap_response):
            result = audit_hcc_gaps(tamara_fhir_context)
        assert isinstance(result["audit_summary"], str)
        assert len(result["audit_summary"]) > 10
