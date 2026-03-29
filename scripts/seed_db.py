"""
scripts/seed_db.py — HCC Risk Navigator Synthetic Data Seeder
==============================================================
Populates the Mock EHR SQLite database with Tamara Williams:
  - Age 68, Medicare Advantage plan
  - Coded: E11.9 (Type 2 Diabetes, HCC 19, RAF 0.104)      ← the CODED problem
  - Note:  "burning sensation in both feet ... Gabapentin"  ← the HCC GAP evidence
  - NOT coded: E11.40 (Diabetic Neuropathy, HCC 18, RAF 0.302)

The "trick" the engine must find:
  The clinical note clearly documents diabetic peripheral neuropathy,
  but the doctor only coded the base E11.9. The HCC engine should catch
  this gap and recommend upgrading to E11.40 (+0.198 RAF delta).

Run:
    python scripts/seed_db.py
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from faker import Faker
from fhir.resources.condition import Condition as FhirCondition
from fhir.resources.documentreference import DocumentReference
from sqlalchemy.orm import Session

from src.database import SessionLocal, init_db
from src.hcc_engine import HCC_MAP
from src.models import ClinicalNote, Condition, Patient

fake = Faker()
Faker.seed(42)


# ─────────────────────────────────────────────────────────────────────────────
# FHIR R4 Builder Helpers
# ─────────────────────────────────────────────────────────────────────────────

def build_fhir_condition(
    fhir_id: str,
    patient_fhir_id: str,
    icd10_code: str,
    description: str,
    onset_date: date,
) -> dict:
    """Build a FHIR R4 Condition resource (v8 compatible)."""
    raw = {
        "resourceType": "Condition",
        "id": fhir_id,
        "clinicalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active",
                "display": "Active",
            }]
        },
        "verificationStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                "code": "confirmed",
                "display": "Confirmed",
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                "code": "problem-list-item",
                "display": "Problem List Item",
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://hl7.org/fhir/sid/icd-10-cm",
                "code": icd10_code,
                "display": description,
            }],
            "text": description,
        },
        "subject": {"reference": f"Patient/{patient_fhir_id}"},
        "onsetDateTime": onset_date.isoformat(),
    }
    parsed = FhirCondition.model_validate(raw)
    return json.loads(parsed.model_dump_json(exclude_none=True))


def build_fhir_document_reference(
    fhir_id: str,
    patient_fhir_id: str,
    note_type: str,
    content_text: str,
    authored_date: date,
) -> dict:
    """Build a FHIR R4 DocumentReference (v8 compatible)."""
    import base64
    encoded = base64.b64encode(content_text.encode()).decode()
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
                "data": encoded,
                "title": note_type,
            }
        }],
    }
    parsed = DocumentReference.model_validate(raw)
    return json.loads(parsed.model_dump_json(exclude_none=True))


# ─────────────────────────────────────────────────────────────────────────────
# Core Seeder
# ─────────────────────────────────────────────────────────────────────────────

TAMARA_FHIR_ID = "tamara-williams-001"

def seed(session: Session) -> Patient:
    """
    Seed Tamara Williams into the Mock EHR.
    Idempotent: skips if Tamara already exists.
    """
    existing = session.query(Patient).filter_by(fhir_id=TAMARA_FHIR_ID).first()
    if existing:
        return existing

    # ── Patient: age 68, Medicare Advantage ─────────────────────────────────
    tamara = Patient(
        fhir_id=TAMARA_FHIR_ID,
        name="Tamara Williams",
        dob="1956-03-12",
        gender="female",
        insurance_plan="Medicare Advantage (CMS CY2024)",
    )
    session.add(tamara)
    session.flush()  # Assigns tamara.id

    # ── Condition: E11.9 — coded, low-RAF ───────────────────────────────────
    # This is what the doctor DID code. HCC 19, RAF 0.104.
    # The system shows this as the current clinical picture.
    e11_9_entry = HCC_MAP["E11.9"]
    e11_9_fhir = build_fhir_condition(
        fhir_id=str(uuid.uuid4()),
        patient_fhir_id=TAMARA_FHIR_ID,
        icd10_code="E11.9",
        description="Type 2 diabetes mellitus without complications",
        onset_date=date.today() - timedelta(days=5 * 365),
    )
    session.add(Condition(
        patient_id=tamara.id,
        fhir_id=e11_9_fhir["id"],
        icd10_code="E11.9",
        description="Type 2 diabetes mellitus without complications",
        hcc_code=e11_9_entry["hcc"],
        raf_weight=e11_9_entry["raf"],
        clinical_status="active",
        onset_date=(date.today() - timedelta(days=5 * 365)).isoformat(),
        fhir_json=json.dumps(e11_9_fhir),
    ))

    # ── Second condition: I10 (Hypertension) — non-HCC filler ───────────────
    i10_entry = HCC_MAP["I10"]
    i10_fhir = build_fhir_condition(
        fhir_id=str(uuid.uuid4()),
        patient_fhir_id=TAMARA_FHIR_ID,
        icd10_code="I10",
        description="Essential (primary) hypertension",
        onset_date=date.today() - timedelta(days=8 * 365),
    )
    session.add(Condition(
        patient_id=tamara.id,
        fhir_id=i10_fhir["id"],
        icd10_code="I10",
        description="Essential (primary) hypertension",
        hcc_code=i10_entry["hcc"],       # 0 — non-HCC
        raf_weight=i10_entry["raf"],     # 0.0
        clinical_status="active",
        onset_date=(date.today() - timedelta(days=8 * 365)).isoformat(),
        fhir_json=json.dumps(i10_fhir),
    ))

    # ── Clinical Note: THE KEY HCC GAP EVIDENCE ──────────────────────────────
    # This note documents diabetic peripheral neuropathy symptoms explicitly
    # but the doctor only coded E11.9, missing E11.40.
    visit_date = date.today() - timedelta(days=14)
    note_content = (
        f"OFFICE VISIT NOTE — {visit_date.strftime('%B %d, %Y')}\n"
        f"Provider: Dr. Emily Nakamura, MD — Internal Medicine\n"
        f"Patient: Tamara Williams | DOB: 1956-03-12 | Medicare ID: 1EG4-TE5-MK72\n"
        f"\n"
        f"REASON FOR VISIT: Routine diabetes management follow-up.\n"
        f"\n"
        f"SUBJECTIVE:\n"
        f"Patient is a 68-year-old female with a known history of Type 2 diabetes mellitus "
        f"and hypertension, presenting for scheduled follow-up. Patient reports worsening "
        f"numbness and a burning sensation in both feet over the last 3 months. She "
        f"describes the pain as a persistent 'pins and needles' feeling, worse at night, "
        f"rating it 5-6/10. She denies any foot ulcers or skin changes. Patient is "
        f"adherent to Metformin 1000mg BID and Lisinopril 10mg daily.\n"
        f"\n"
        f"OBJECTIVE:\n"
        f"Vitals: BP 138/86 mmHg, HR 72 bpm, Weight 165 lbs, BMI 27.4\n"
        f"Fasting glucose: 186 mg/dL. HbA1c: 8.2%.\n"
        f"Neurological: Reduced vibration sense in bilateral lower extremities. "
        f"Monofilament test: absent sensation at plantar surface of both feet. "
        f"Bilateral lower extremity reflexes diminished.\n"
        f"\n"
        f"ASSESSMENT AND PLAN:\n"
        f"1. Type 2 Diabetes Mellitus — poorly controlled (HbA1c 8.2%).\n"
        f"   - Continue Metformin 1000mg BID. Consider adding GLP-1 agonist.\n"
        f"2. Peripheral neuropathy symptoms — bilateral feet, clinically consistent\n"
        f"   with diabetic peripheral neuropathy given diabetes history and\n"
        f"   neurological exam findings.\n"
        f"   - Initiate Gabapentin 300mg TID for neuropathic pain management.\n"
        f"   - Refer to podiatry for foot care education.\n"
        f"3. Hypertension — continue current regimen, BP slightly elevated today.\n"
        f"\n"
        f"Patient educated on diabetic foot care. Follow-up in 6 weeks.\n"
        f"\n"
        f"Dr. Emily Nakamura, MD\n"
        f"Board Certified — Internal Medicine"
    )

    note_fhir = build_fhir_document_reference(
        fhir_id=str(uuid.uuid4()),
        patient_fhir_id=TAMARA_FHIR_ID,
        note_type="Office Visit Note",
        content_text=note_content,
        authored_date=visit_date,
    )
    session.add(ClinicalNote(
        patient_id=tamara.id,
        fhir_id=note_fhir["id"],
        note_type="Office Visit Note",
        content=note_content,
        authored_date=visit_date.isoformat(),
        author="Dr. Emily Nakamura, MD",
        fhir_json=json.dumps(note_fhir),
    ))

    session.commit()
    return tamara


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🌱 Initializing HCC Risk Navigator database schema...")
    init_db()

    print("🩺 Seeding Tamara Williams (Medicare Advantage, HCC gap patient)...")
    with SessionLocal() as session:
        patient = seed(session)
        patient_name = patient.name
        patient_fhir_id = patient.fhir_id

    print(f"✅ Done! Patient '{patient_name}' (FHIR ID: {patient_fhir_id}) seeded.")
    print("   - Coded: E11.9 (HCC 19, RAF 0.104)")
    print("   - Note: 'burning sensation... Gabapentin' → gap: E11.40 (HCC 18, RAF 0.302)")
    print("   Database: data/mock_ehr.sqlite")
