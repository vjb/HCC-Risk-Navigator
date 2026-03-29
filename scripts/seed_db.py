"""
scripts/seed_db.py — Synthetic FHIR R4 Data Seeder
====================================================
Generates realistic (but entirely synthetic) patient data for patient "Tamara"
and populates the Mock EHR SQLite database.

Run directly:
    python scripts/seed_db.py

OR import the seed() function for use in tests with a custom session.
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

# Allow running from project root: python scripts/seed_db.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from faker import Faker
from fhir.resources.documentreference import DocumentReference
from fhir.resources.medicationrequest import MedicationRequest as FhirMR
from fhir.resources.observation import Observation as FhirObs
from sqlalchemy.orm import Session

from src.database import SessionLocal, init_db
from src.models import ClinicalNote, MedicationRequest, Observation, Patient

fake = Faker()
Faker.seed(42)  # Deterministic output for reproducibility


# ─────────────────────────────────────────────────────────────────────────────
# FHIR R4 Builder Helpers
# fhir.resources v8 breaking changes:
#   - MedicationRequest.medication is now a CodeableReference (not medicationCodeableConcept)
#   - DocumentReference.date must be a full ISO datetime string with timezone
# ─────────────────────────────────────────────────────────────────────────────

def build_medication_request_fhir(
    fhir_id: str,
    patient_fhir_id: str,
    medication_name: str,
    rxnorm_code: str,
    dosage_text: str,
    start_date: date,
    end_date: date,
    status: str = "completed",
) -> dict:
    """
    Build a FHIR R4 MedicationRequest dict compatible with fhir.resources v8+.
    v8 uses CodeableReference for the medication field.
    """
    raw = {
        "resourceType": "MedicationRequest",
        "id": fhir_id,
        "status": status,
        "intent": "order",
        "medication": {
            "concept": {
                "coding": [{
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": rxnorm_code,
                    "display": medication_name,
                }],
                "text": medication_name,
            }
        },
        "subject": {"reference": f"Patient/{patient_fhir_id}"},
        "authoredOn": start_date.isoformat(),
        "dosageInstruction": [{"text": dosage_text}],
        "dispenseRequest": {
            "validityPeriod": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            }
        },
    }
    parsed = FhirMR.model_validate(raw)
    return json.loads(parsed.model_dump_json(exclude_none=True))


def build_observation_fhir(
    fhir_id: str,
    patient_fhir_id: str,
    loinc_code: str,
    display: str,
    value: float,
    unit: str,
    effective_date: date,
) -> dict:
    """Build and validate a FHIR R4 Observation dict."""
    raw = {
        "resourceType": "Observation",
        "id": fhir_id,
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "laboratory",
                "display": "Laboratory",
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": loinc_code,
                "display": display,
            }],
            "text": display,
        },
        "subject": {"reference": f"Patient/{patient_fhir_id}"},
        "effectiveDateTime": effective_date.isoformat(),
        "valueQuantity": {
            "value": value,
            "unit": unit,
            "system": "http://unitsofmeasure.org",
            "code": unit,
        },
    }
    parsed = FhirObs.model_validate(raw)
    return json.loads(parsed.model_dump_json(exclude_none=True))


def build_document_reference_fhir(
    fhir_id: str,
    patient_fhir_id: str,
    note_type: str,
    content_text: str,
    authored_date: date,
) -> dict:
    """
    Build a FHIR R4 DocumentReference dict.
    v8: date field requires a full ISO datetime string with timezone offset.
    """
    import base64
    encoded_content = base64.b64encode(content_text.encode()).decode()
    raw = {
        "resourceType": "DocumentReference",
        "id": fhir_id,
        "status": "current",
        "type": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "11506-3",
                "display": note_type,
            }],
            "text": note_type,
        },
        "subject": {"reference": f"Patient/{patient_fhir_id}"},
        "date": f"{authored_date.isoformat()}T00:00:00+00:00",
        "content": [{
            "attachment": {
                "contentType": "text/plain",
                "data": encoded_content,
                "title": note_type,
            }
        }],
    }
    parsed = DocumentReference.model_validate(raw)
    return json.loads(parsed.model_dump_json(exclude_none=True))


# ─────────────────────────────────────────────────────────────────────────────
# Core Seeder
# ─────────────────────────────────────────────────────────────────────────────

def seed(session: Session) -> Patient:
    """
    Seed the database with Tamara's complete FHIR timeline.
    Idempotent: skips if Tamara already exists (matched by fhir_id).
    Returns the Patient ORM object.
    """
    TAMARA_FHIR_ID = "tamara-chen-001"

    # ── Idempotency check ────────────────────────────────────────────────────
    existing = session.query(Patient).filter_by(fhir_id=TAMARA_FHIR_ID).first()
    if existing:
        return existing

    # ── Patient Demographics ─────────────────────────────────────────────────
    tamara = Patient(
        fhir_id=TAMARA_FHIR_ID,
        name="Tamara Chen",
        dob="1978-04-15",
        gender="female",
    )
    session.add(tamara)
    session.flush()  # Get tamara.id assigned

    # ── Metformin Course — 2 months (≈60 days), completed ───────────────────
    # Step-therapy clock: started 4 months ago, lasted only ~2 months
    # This is KEY: Aetna requires 6 months, but Tamara only managed 2 months
    # due to GI intolerance.
    course_start = date.today() - timedelta(days=120)
    course_end = course_start + timedelta(days=61)

    met_fhir = build_medication_request_fhir(
        fhir_id=str(uuid.uuid4()),
        patient_fhir_id=TAMARA_FHIR_ID,
        medication_name="Metformin 500 MG Oral Tablet",
        rxnorm_code="861007",
        dosage_text="500mg twice daily by mouth with meals",
        start_date=course_start,
        end_date=course_end,
        status="completed",
    )
    session.add(MedicationRequest(
        patient_id=tamara.id,
        fhir_id=met_fhir["id"],
        medication_name="Metformin 500 MG Oral Tablet",
        dosage="500mg twice daily",
        start_date=course_start.isoformat(),
        end_date=course_end.isoformat(),
        status="completed",
        fhir_json=json.dumps(met_fhir),
    ))

    # ── A1C Lab Results — 3 readings showing poor glycemic control ───────────
    a1c_schedule = [
        (date.today() - timedelta(days=150), 7.8),   # Baseline (pre-Metformin)
        (date.today() - timedelta(days=90),  8.1),   # On Metformin (GI issues starting)
        (date.today() - timedelta(days=30),  8.6),   # After discontinuation (rising)
    ]
    for obs_date, a1c_value in a1c_schedule:
        obs_fhir = build_observation_fhir(
            fhir_id=str(uuid.uuid4()),
            patient_fhir_id=TAMARA_FHIR_ID,
            loinc_code="4548-4",
            display="Hemoglobin A1c/Hemoglobin.total in Blood",
            value=a1c_value,
            unit="%",
            effective_date=obs_date,
        )
        session.add(Observation(
            patient_id=tamara.id,
            fhir_id=obs_fhir["id"],
            loinc_code="4548-4",
            display="Hemoglobin A1c/Hemoglobin.total in Blood",
            value=a1c_value,
            unit="%",
            effective_date=obs_date.isoformat(),
            fhir_json=json.dumps(obs_fhir),
        ))

    # ── Clinical Notes — GI Intolerance Evidence ─────────────────────────────
    note_content = (
        "PROGRESS NOTE — Primary Care Visit\n"
        "Date: {note_date}\n"
        "Provider: Dr. Sarah Morrison, MD\n\n"
        "SUBJECTIVE:\n"
        "Patient Tamara Chen (DOB: 1978-04-15) presents as a follow-up for Type 2 Diabetes "
        "management. Patient reports severe GI intolerance since initiating Metformin "
        "therapy 8 weeks ago. Symptoms include persistent nausea, abdominal cramping, and "
        "diarrhea occurring within 30-60 minutes of each dose. Symptoms significantly impact "
        "daily functioning and have not improved despite dose adjustments.\n\n"
        "OBJECTIVE:\n"
        "Weight: 172 lbs. BP: 128/82 mmHg. A1C today: 8.1%.\n\n"
        "ASSESSMENT AND PLAN:\n"
        "1. Type 2 Diabetes Mellitus — poorly controlled.\n"
        "2. Metformin 500mg BID — DISCONTINUED due to severe gastrointestinal adverse effects "
        "causing patient non-adherence. GI intolerance documented as primary reason for "
        "inability to complete required step-therapy course.\n"
        "3. Patient counseled regarding alternative GLP-1 receptor agonist therapy "
        "(semaglutide/Ozempic) which may also provide cardiovascular benefit.\n"
        "4. Prior Authorization request to be initiated for Ozempic (semaglutide 0.5mg weekly "
        "subcutaneous injection). Clinical exception supported by documented Metformin "
        "GI intolerance and failure to tolerate step-therapy requirement.\n\n"
        "Dr. Sarah Morrison, MD\nBoard Certified — Internal Medicine & Endocrinology"
    ).format(note_date=(date.today() - timedelta(days=90)).isoformat())

    note_fhir = build_document_reference_fhir(
        fhir_id=str(uuid.uuid4()),
        patient_fhir_id=TAMARA_FHIR_ID,
        note_type="Progress Note",
        content_text=note_content,
        authored_date=date.today() - timedelta(days=90),
    )
    session.add(ClinicalNote(
        patient_id=tamara.id,
        fhir_id=note_fhir["id"],
        note_type="Progress Note",
        content=note_content,
        authored_date=(date.today() - timedelta(days=90)).isoformat(),
        author="Dr. Sarah Morrison, MD",
        fhir_json=json.dumps(note_fhir),
    ))

    session.commit()
    return tamara


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🌱 Initializing database schema...")
    init_db()

    print("🩺 Seeding synthetic patient data for Tamara Chen...")
    with SessionLocal() as session:
        patient = seed(session)
        patient_name = patient.name
        patient_fhir_id = patient.fhir_id

    print(f"✅ Done! Patient '{patient_name}' (FHIR ID: {patient_fhir_id}) seeded successfully.")
    print("   Database: data/mock_ehr.sqlite")
