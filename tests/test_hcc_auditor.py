"""
tests/test_hcc_auditor.py — HCC Engine deterministic unit tests.

The hcc_engine module performs pure FHIR data extraction + RAF computation.
No LLM calls are made — Po's agent performs the CDI gap analysis using the
structured clinical context this engine returns.

Tests assert that audit_hcc_gaps():
  1. Correctly computes current RAF from coded conditions (deterministic).
  2. Returns all required output keys.
  3. Returns clinical_notes_text for Po's agent to review.
  4. Returns hcc_reference_v28 as context for Po's agent.
  5. Always returns gaps=[] and gap_count=0 (gaps are found by Po, not the engine).
  6. Handles patients with no notes or no conditions gracefully.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.hcc_engine import audit_hcc_gaps, compute_raf, HCC_MAP


# ─────────────────────────────────────────────────────────────────────────────
# Shared FHIR fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def tamara_fhir_context() -> dict:
    """Standard Tamara Williams FHIR context: one coded condition, one clinical note."""
    return {
        "patient": {
            "resourceType": "Patient",
            "id": "tamara-williams-001",
            "name": [{"use": "official", "text": "Tamara Williams"}],
            "birthDate": "1956-03-12",
            "gender": "female",
            "extension": [
                {"url": "http://promptopinion.com/fhir/insurance-plan",
                 "valueString": "Medicare Advantage"}
            ],
        },
        "conditions": [
            {
                "resourceType": "Condition",
                "id": "condition-1",
                "clinicalStatus": {"coding": [{"code": "active"}]},
                "code": {
                    "coding": [{
                        "system": "http://hl7.org/fhir/sid/icd-10-cm",
                        "code": "E11.9",
                        "display": "Type 2 diabetes mellitus without complications",
                    }],
                    "text": "Type 2 diabetes mellitus without complications",
                },
                "extension": [
                    {"url": "http://promptopinion.com/fhir/hcc-code",     "valueInteger": 19},
                    {"url": "http://promptopinion.com/fhir/raf-weight", "valueDecimal": 0.104},
                ],
            }
        ],
        "clinical_notes": [
            {
                "resourceType": "DocumentReference",
                "id": "note-1",
                "type": {"text": "Office Visit Note"},
                "date": (date.today() - timedelta(days=14)).isoformat(),
                "author": [{"display": "Dr. Nakamura"}],
                "content": [{"attachment": {"contentType": "text/plain", "data": (
                    "Patient is a 68-year-old female with known Type 2 diabetes presenting "
                    "for routine follow-up. Patient complains of worsening numbness and a "
                    "burning sensation in both feet over the last 3 months. Bilateral lower "
                    "extremity involved. Symptoms consistent with peripheral neuropathy. "
                    "Gabapentin 300mg TID prescribed for symptom management. "
                    "Patient to follow up in 6 weeks."
                )}}],
            }
        ],
    }


@pytest.fixture()
def empty_fhir_context() -> dict:
    """Patient with no conditions and no clinical notes."""
    return {
        "patient": {
            "resourceType": "Patient",
            "id": "empty-patient-001",
            "name": [{"text": "Empty Patient"}],
        },
        "conditions":     [],
        "clinical_notes": [],
    }


@pytest.fixture()
def multi_condition_context() -> dict:
    """Patient with multiple HCC-coded conditions."""
    return {
        "patient": {
            "resourceType": "Patient",
            "id": "multi-001",
            "name": [{"text": "Multi Condition"}],
        },
        "conditions": [
            {
                "resourceType": "Condition",
                "code": {"coding": [{"code": "E11.9", "display": "T2DM"}]},
            },
            {
                "resourceType": "Condition",
                "code": {"coding": [{"code": "I50.9", "display": "Heart failure"}]},
            },
            {
                "resourceType": "Condition",
                "code": {"coding": [{"code": "N18.3", "display": "CKD Stage 3"}]},
            },
        ],
        "clinical_notes": [],
    }


# ─────────────────────────────────────────────────────────────────────────────
# TestComputeRAF — pure deterministic unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeRAF:
    def test_single_hcc_code(self):
        """E11.9 alone should yield RAF 0.104."""
        assert abs(compute_raf(["E11.9"]) - 0.104) < 0.001

    def test_multiple_hcc_codes(self):
        """E11.9 + I50.9 should sum their RAFs."""
        expected = 0.104 + 0.331
        assert abs(compute_raf(["E11.9", "I50.9"]) - expected) < 0.001

    def test_no_duplicate_hcc_codes(self):
        """E11.9 (HCC 19) and E11.65 (HCC 18) are different HCCs — both counted."""
        expected = 0.104 + 0.302
        assert abs(compute_raf(["E11.9", "E11.65"]) - expected) < 0.001

    def test_non_hcc_code_excluded(self):
        """I10 (hypertension) has HCC 0 and must not add to RAF."""
        assert compute_raf(["I10"]) == 0.0

    def test_empty_code_list(self):
        assert compute_raf([]) == 0.0

    def test_unknown_code_ignored(self):
        assert compute_raf(["Z99.99Z"]) == 0.0

    def test_three_hcc_codes_sum_correctly(self):
        """E11.9 + I50.9 + N18.3 should sum to 0.104 + 0.331 + 0.289 = 0.724."""
        expected = 0.104 + 0.331 + 0.289
        assert abs(compute_raf(["E11.9", "I50.9", "N18.3"]) - expected) < 0.001


# ─────────────────────────────────────────────────────────────────────────────
# TestAuditOutputStructure — required keys and types
# ─────────────────────────────────────────────────────────────────────────────

class TestAuditOutputStructure:
    """The audit result must always have a predictable, complete shape."""

    REQUIRED_KEYS = {
        "patient_id", "patient_name",
        "current_raf", "projected_raf", "raf_delta",
        "existing_codes", "coded_conditions_detail",
        "clinical_notes_text", "note_count",
        "hcc_reference_v28",
        "gaps", "gap_count",
        "audit_summary",
    }

    def test_all_required_keys_present(self, tamara_fhir_context):
        result = audit_hcc_gaps(tamara_fhir_context)
        missing = self.REQUIRED_KEYS - result.keys()
        assert not missing, f"audit_hcc_gaps() missing keys: {missing}"

    def test_patient_name_is_tamara(self, tamara_fhir_context):
        result = audit_hcc_gaps(tamara_fhir_context)
        assert "Tamara" in result["patient_name"]

    def test_patient_id_is_correct(self, tamara_fhir_context):
        result = audit_hcc_gaps(tamara_fhir_context)
        assert result["patient_id"] == "tamara-williams-001"

    def test_existing_codes_is_list(self, tamara_fhir_context):
        result = audit_hcc_gaps(tamara_fhir_context)
        assert isinstance(result["existing_codes"], list)

    def test_existing_codes_contains_e11_9(self, tamara_fhir_context):
        result = audit_hcc_gaps(tamara_fhir_context)
        assert "E11.9" in result["existing_codes"]

    def test_gaps_is_always_empty_list(self, tamara_fhir_context):
        """Gaps are populated by Po's agent — the engine always returns []."""
        result = audit_hcc_gaps(tamara_fhir_context)
        assert result["gaps"] == []
        assert result["gap_count"] == 0

    def test_audit_summary_is_non_empty_string(self, tamara_fhir_context):
        result = audit_hcc_gaps(tamara_fhir_context)
        assert isinstance(result["audit_summary"], str)
        assert len(result["audit_summary"]) > 10

    def test_raf_delta_is_zero_no_llm_analysis(self, tamara_fhir_context):
        """Before Po's agent analysis, raf_delta is always 0.0."""
        result = audit_hcc_gaps(tamara_fhir_context)
        assert result["raf_delta"] == 0.0

    def test_projected_raf_equals_current_raf_before_analysis(self, tamara_fhir_context):
        result = audit_hcc_gaps(tamara_fhir_context)
        assert result["projected_raf"] == result["current_raf"]


# ─────────────────────────────────────────────────────────────────────────────
# TestRAFComputation — deterministic RAF from FHIR conditions
# ─────────────────────────────────────────────────────────────────────────────

class TestRAFComputation:
    def test_current_raf_is_0_104_for_e11_9_only(self, tamara_fhir_context):
        """Tamara has only E11.9 coded — RAF must be 0.104."""
        result = audit_hcc_gaps(tamara_fhir_context)
        assert abs(result["current_raf"] - 0.104) < 0.001

    def test_empty_patient_has_zero_raf(self, empty_fhir_context):
        result = audit_hcc_gaps(empty_fhir_context)
        assert result["current_raf"] == 0.0

    def test_multi_condition_raf_is_summed(self, multi_condition_context):
        """E11.9 + I50.9 + N18.3 → RAF 0.104 + 0.331 + 0.289 = 0.724."""
        result = audit_hcc_gaps(multi_condition_context)
        expected = 0.104 + 0.331 + 0.289
        assert abs(result["current_raf"] - expected) < 0.001

    def test_coded_conditions_detail_includes_hcc_info(self, tamara_fhir_context):
        """coded_conditions_detail must have icd10, hcc_code, raf_weight."""
        result = audit_hcc_gaps(tamara_fhir_context)
        assert len(result["coded_conditions_detail"]) > 0
        detail = result["coded_conditions_detail"][0]
        assert "icd10"      in detail
        assert "hcc_code"   in detail
        assert "raf_weight" in detail
        assert detail["icd10"] == "E11.9"
        assert detail["hcc_code"] == 19
        assert abs(detail["raf_weight"] - 0.104) < 0.001


# ─────────────────────────────────────────────────────────────────────────────
# TestClinicalNotesContext — Po's agent CDI data
# ─────────────────────────────────────────────────────────────────────────────

class TestClinicalNotesContext:
    """
    The engine must return rich clinical context so Po's agent can do CDI analysis.
    These tests validate the data that Po's LLM will act on.
    """

    def test_clinical_notes_text_is_non_empty(self, tamara_fhir_context):
        """clinical_notes_text must contain the note content."""
        result = audit_hcc_gaps(tamara_fhir_context)
        assert len(result["clinical_notes_text"]) > 50

    def test_clinical_notes_text_contains_key_evidence(self, tamara_fhir_context):
        """The burning feet evidence must be in clinical_notes_text for Po to analyze."""
        result = audit_hcc_gaps(tamara_fhir_context)
        notes = result["clinical_notes_text"].lower()
        assert "burning" in notes or "neuropathy" in notes or "gabapentin" in notes, (
            "Key neuropathy evidence missing from clinical_notes_text"
        )

    def test_clinical_notes_text_includes_author_and_date(self, tamara_fhir_context):
        """Notes must be labelled with author/date for attribution."""
        result = audit_hcc_gaps(tamara_fhir_context)
        assert "Dr. Nakamura" in result["clinical_notes_text"]

    def test_note_count_is_correct(self, tamara_fhir_context):
        result = audit_hcc_gaps(tamara_fhir_context)
        assert result["note_count"] == 1

    def test_empty_patient_notes_text_is_placeholder(self, empty_fhir_context):
        """A patient with no notes should return a clear placeholder."""
        result = audit_hcc_gaps(empty_fhir_context)
        assert "No clinical notes" in result["clinical_notes_text"]
        assert result["note_count"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# TestHCCReference — V28 reference table for Po's agent
# ─────────────────────────────────────────────────────────────────────────────

class TestHCCReference:
    """
    Po's agent uses hcc_reference_v28 to map clinical findings to ICD-10 codes.
    These tests ensure the reference is correct and complete.
    """

    def test_hcc_reference_is_dict(self, tamara_fhir_context):
        result = audit_hcc_gaps(tamara_fhir_context)
        assert isinstance(result["hcc_reference_v28"], dict)

    def test_hcc_reference_includes_e11_40(self, tamara_fhir_context):
        """E11.40 (the neuropathy upgrade code) must be in the reference."""
        result = audit_hcc_gaps(tamara_fhir_context)
        assert "E11.40" in result["hcc_reference_v28"]

    def test_hcc_reference_excludes_non_hcc_codes(self, tamara_fhir_context):
        """I10 (hypertension, HCC 0) should not appear in the reference."""
        result = audit_hcc_gaps(tamara_fhir_context)
        assert "I10" not in result["hcc_reference_v28"]

    def test_hcc_reference_entry_has_correct_shape(self, tamara_fhir_context):
        """Each reference entry must have hcc, label, raf."""
        result = audit_hcc_gaps(tamara_fhir_context)
        entry = result["hcc_reference_v28"]["E11.40"]
        assert "hcc"   in entry
        assert "label" in entry
        assert "raf"   in entry
        assert entry["hcc"] == 18
        assert abs(entry["raf"] - 0.302) < 0.001

    def test_hcc_reference_all_entries_have_positive_hcc(self, tamara_fhir_context):
        """All entries in the reference must have hcc > 0."""
        result = audit_hcc_gaps(tamara_fhir_context)
        for code, entry in result["hcc_reference_v28"].items():
            assert entry["hcc"] > 0, f"{code} has hcc=0 but is in the reference"
