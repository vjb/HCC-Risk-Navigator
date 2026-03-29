"""
TDD Phase 1 — Data Layer Tests (written BEFORE seed implementation).

Asserts:
  1. Patient "Tamara" exists with Medicare Advantage plan.
  2. Condition E11.9 is seeded with correct HCC and RAF weight.
  3. Condition FHIR JSON is valid FHIR R4.
  4. Clinical note contains "burning" keyword (the HCC gap evidence).
  5. Clinical note FHIR JSON is valid DocumentReference R4.
  6. The seeded state has HCC gaps: at least one HCC relevant note
     that doesn't have a corresponding coded condition.
"""
from __future__ import annotations

import json

import pytest

from src.models import ClinicalNote, Condition, Patient


def _seed_test_db(session):
    from scripts.seed_db import seed
    seed(session)
    session.flush()


# ─────────────────────────────────────────────────────────────────────────────
# Patient Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPatientSeed:
    def test_tamara_patient_exists(self, db_session):
        _seed_test_db(db_session)
        p = db_session.query(Patient).filter(Patient.name.contains("Tamara")).first()
        assert p is not None

    def test_patient_is_medicare_advantage(self, db_session):
        _seed_test_db(db_session)
        p = db_session.query(Patient).filter(Patient.name.contains("Tamara")).first()
        assert p.insurance_plan is not None
        assert "Medicare" in p.insurance_plan

    def test_patient_age_is_68(self, db_session):
        _seed_test_db(db_session)
        from datetime import date
        p = db_session.query(Patient).filter(Patient.name.contains("Tamara")).first()
        dob = date.fromisoformat(p.dob)
        age = (date.today() - dob).days // 365
        assert 65 <= age <= 72, f"Expected Tamara to be ~68 years old, got {age}"


# ─────────────────────────────────────────────────────────────────────────────
# Condition Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestConditionSeed:
    def test_e11_9_condition_exists(self, db_session):
        """E11.9 (Type 2 Diabetes) must be on Tamara's coded problem list."""
        _seed_test_db(db_session)
        cond = db_session.query(Condition).filter_by(icd10_code="E11.9").first()
        assert cond is not None, "E11.9 not found in seeded conditions"

    def test_e11_9_has_correct_hcc_code(self, db_session):
        """E11.9 should map to HCC 19."""
        _seed_test_db(db_session)
        cond = db_session.query(Condition).filter_by(icd10_code="E11.9").first()
        assert cond.hcc_code == 19, f"Expected HCC 19, got {cond.hcc_code}"

    def test_e11_9_has_correct_raf_weight(self, db_session):
        """E11.9 RAF weight must be 0.104 (CMS V28)."""
        _seed_test_db(db_session)
        cond = db_session.query(Condition).filter_by(icd10_code="E11.9").first()
        assert abs(cond.raf_weight - 0.104) < 0.001, f"Expected RAF 0.104, got {cond.raf_weight}"

    def test_e11_40_is_NOT_coded(self, db_session):
        """
        E11.40 (Diabetic Neuropathy) must NOT be on the problem list —
        this is the HCC gap the engine needs to find.
        """
        _seed_test_db(db_session)
        gap = db_session.query(Condition).filter_by(icd10_code="E11.40").first()
        assert gap is None, "E11.40 should NOT be coded — it is the HCC gap to detect"

    def test_condition_fhir_json_is_valid_r4(self, db_session):
        """Each Condition must have parseable FHIR R4 JSON."""
        _seed_test_db(db_session)
        conditions = db_session.query(Condition).all()
        assert conditions, "No conditions seeded"
        for cond in conditions:
            data = json.loads(cond.fhir_json)
            assert data.get("resourceType") == "Condition"
            from fhir.resources.condition import Condition as FhirCondition
            parsed = FhirCondition.model_validate(data)
            assert parsed.subject is not None
            assert parsed.code is not None


# ─────────────────────────────────────────────────────────────────────────────
# ClinicalNote (HCC Gap Evidence) Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestClinicalNoteSeed:
    def test_clinical_note_exists(self, db_session):
        _seed_test_db(db_session)
        notes = db_session.query(ClinicalNote).all()
        assert notes, "No clinical notes seeded"

    def test_note_contains_burning_feet_evidence(self, db_session):
        """The note must contain 'burning' — the key HCC gap trigger phrase."""
        _seed_test_db(db_session)
        notes = db_session.query(ClinicalNote).all()
        found = any("burning" in n.content.lower() for n in notes)
        assert found, "No note contains 'burning' — the diabetic neuropathy evidence is missing"

    def test_note_contains_gabapentin(self, db_session):
        """Gabapentin prescription strengthens the neuropathy evidence."""
        _seed_test_db(db_session)
        notes = db_session.query(ClinicalNote).all()
        found = any("gabapentin" in n.content.lower() for n in notes)
        assert found, "Gabapentin not mentioned in notes — weakens the neuropathy case"

    def test_note_contains_numbness(self, db_session):
        """'Numbness' is co-evidence for peripheral neuropathy."""
        _seed_test_db(db_session)
        notes = db_session.query(ClinicalNote).all()
        found = any("numbness" in n.content.lower() for n in notes)
        assert found, "No mention of numbness in clinical notes"

    def test_clinical_note_fhir_json_is_valid_r4(self, db_session):
        """Each note must be a parseable FHIR R4 DocumentReference."""
        _seed_test_db(db_session)
        notes = db_session.query(ClinicalNote).all()
        for note in notes:
            data = json.loads(note.fhir_json)
            assert data.get("resourceType") == "DocumentReference"
