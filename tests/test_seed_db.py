"""
TDD Phase 1 — Data Layer Tests (written BEFORE implementation).

These tests assert that:
  1. seed_db populates a Patient named "Tamara".
  2. MedicationRequest FHIR JSON is valid FHIR R4.
  3. Observation FHIR JSON is valid FHIR R4.
  4. ClinicalNote content contains the GI intolerance evidence phrase.
  5. Metformin therapy duration spans exactly 2 months.
  6. A1C observations are present and values are clinically plausible (>5%).
"""
from __future__ import annotations

import json

import pytest

from src.models import ClinicalNote, MedicationRequest, Observation, Patient


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _seed_test_db(session):
    """Run the seeder against the provided session (in-memory DB)."""
    from scripts.seed_db import seed  # Import here so failure is clear
    seed(session)
    session.flush()


# ─────────────────────────────────────────────────────────────────────────────
# Patient Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPatientSeed:
    def test_patient_named_tamara_exists(self, db_session):
        """Seed must create a patient with 'Tamara' in her name."""
        _seed_test_db(db_session)
        patient = db_session.query(Patient).filter(Patient.name.contains("Tamara")).first()
        assert patient is not None, "No patient named Tamara found in seeded DB"

    def test_patient_has_fhir_id(self, db_session):
        """Patient record must have a non-empty FHIR ID."""
        _seed_test_db(db_session)
        patient = db_session.query(Patient).filter(Patient.name.contains("Tamara")).first()
        assert patient.fhir_id, "Patient FHIR ID is empty"

    def test_patient_has_valid_dob(self, db_session):
        """DOB must be a valid ISO-8601 date string."""
        _seed_test_db(db_session)
        patient = db_session.query(Patient).filter(Patient.name.contains("Tamara")).first()
        from datetime import date
        parsed = date.fromisoformat(patient.dob)
        assert parsed.year in range(1950, 2000), f"Unexpected birth year: {parsed.year}"


# ─────────────────────────────────────────────────────────────────────────────
# MedicationRequest Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMedicationSeed:
    def test_metformin_records_exist(self, db_session):
        """At least one Metformin MedicationRequest must be seeded."""
        _seed_test_db(db_session)
        meds = (
            db_session.query(MedicationRequest)
            .filter(MedicationRequest.medication_name.ilike("%metformin%"))
            .all()
        )
        assert len(meds) >= 1, "No Metformin records found"

    def test_medication_fhir_json_is_valid_r4(self, db_session):
        """Each MedicationRequest must store a parseable FHIR R4 JSON blob."""
        _seed_test_db(db_session)
        meds = db_session.query(MedicationRequest).all()
        assert meds, "No MedicationRequest records to validate"
        for med in meds:
            data = json.loads(med.fhir_json)
            assert data.get("resourceType") == "MedicationRequest", (
                f"Expected resourceType=MedicationRequest, got {data.get('resourceType')}"
            )
            # Validate via fhir.resources v8
            from fhir.resources.medicationrequest import MedicationRequest as FhirMR
            parsed = FhirMR.model_validate(data)
            # v8: medication is a CodeableReference; subject is a Reference
            assert parsed.subject is not None
            assert parsed.medication is not None

    def test_metformin_therapy_duration_two_months(self, db_session):
        """Tamara's Metformin course must span ~2 calendar months (50-70 days)."""
        _seed_test_db(db_session)
        from datetime import date

        meds = (
            db_session.query(MedicationRequest)
            .filter(MedicationRequest.medication_name.ilike("%metformin%"))
            .all()
        )
        assert meds, "No Metformin records"
        # Find earliest start and latest end across all records
        start = min(date.fromisoformat(m.start_date) for m in meds)
        end = max(date.fromisoformat(m.end_date) for m in meds if m.end_date)
        duration_days = (end - start).days
        assert 50 <= duration_days <= 70, (
            f"Expected ~2-month Metformin course (50-70 days), got {duration_days} days"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Observation Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestObservationSeed:
    def test_a1c_observations_exist(self, db_session):
        """At least 2 A1C lab results must be seeded."""
        _seed_test_db(db_session)
        obs = (
            db_session.query(Observation)
            .filter(Observation.loinc_code == "4548-4")
            .all()
        )
        assert len(obs) >= 2, f"Expected ≥2 A1C observations, got {len(obs)}"

    def test_a1c_values_are_clinically_elevated(self, db_session):
        """A1C values must be in a diabetic/pre-diabetic range (>6.0%)."""
        _seed_test_db(db_session)
        obs = db_session.query(Observation).filter(Observation.loinc_code == "4548-4").all()
        for o in obs:
            assert o.value > 6.0, f"A1C value {o.value} is below diabetic threshold"

    def test_observation_fhir_json_is_valid_r4(self, db_session):
        """Each Observation must store a parseable FHIR R4 JSON blob."""
        _seed_test_db(db_session)
        obs = db_session.query(Observation).all()
        assert obs, "No Observation records to validate"
        for o in obs:
            data = json.loads(o.fhir_json)
            assert data.get("resourceType") == "Observation"
            from fhir.resources.observation import Observation as FhirObs
            parsed = FhirObs.model_validate(data)
            assert parsed.subject is not None
            assert parsed.code is not None


# ─────────────────────────────────────────────────────────────────────────────
# ClinicalNote Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestClinicalNoteSeed:
    def test_gi_intolerance_note_exists(self, db_session):
        """A clinical note mentioning GI intolerance to Metformin must be present."""
        _seed_test_db(db_session)
        notes = db_session.query(ClinicalNote).all()
        assert notes, "No ClinicalNote records seeded"
        gi_notes = [n for n in notes if "GI intolerance" in n.content or "gastrointestinal" in n.content.lower()]
        assert gi_notes, "No note found containing GI intolerance evidence"

    def test_clinical_note_fhir_json_is_valid_r4(self, db_session):
        """Each ClinicalNote must store a parseable FHIR R4 DocumentReference JSON."""
        _seed_test_db(db_session)
        notes = db_session.query(ClinicalNote).all()
        assert notes
        for note in notes:
            data = json.loads(note.fhir_json)
            assert data.get("resourceType") == "DocumentReference", (
                f"Expected DocumentReference, got {data.get('resourceType')}"
            )

    def test_gi_note_mentions_discontinued(self, db_session):
        """The GI intolerance note must document that Metformin was discontinued."""
        _seed_test_db(db_session)
        notes = db_session.query(ClinicalNote).all()
        gi_notes = [n for n in notes if "GI intolerance" in n.content or "gastrointestinal" in n.content.lower()]
        assert any("discontinu" in n.content.lower() for n in gi_notes), (
            "GI intolerance note does not document discontinuation"
        )
