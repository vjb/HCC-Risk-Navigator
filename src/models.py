"""
SQLAlchemy ORM models for the HCC Risk Navigator Mock EHR.
Focused on the two data types needed: FHIR Conditions (coded diagnoses)
and FHIR DocumentReferences (unstructured clinical notes).
"""
from __future__ import annotations

import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Patient(Base):
    """Core patient demographics — Medicare Advantage member."""

    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fhir_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    dob = Column(String(10), nullable=False)           # ISO-8601
    gender = Column(String(20), nullable=False)
    insurance_plan = Column(String(80), nullable=True) # e.g. "Medicare Advantage"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    conditions = relationship("Condition", back_populates="patient", cascade="all, delete-orphan")
    clinical_notes = relationship("ClinicalNote", back_populates="patient", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Patient fhir_id={self.fhir_id!r} name={self.name!r}>"


class Condition(Base):
    """
    FHIR Condition — a structured, coded diagnosis on the patient's problem list.
    Each condition maps to an ICD-10 code and optionally an HCC code + RAF weight.
    """

    __tablename__ = "conditions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    fhir_id = Column(String(64), unique=True, nullable=False)
    icd10_code = Column(String(16), nullable=False)    # e.g. "E11.9"
    description = Column(String(200), nullable=False)  # e.g. "Type 2 diabetes mellitus..."
    hcc_code = Column(Integer, nullable=True)           # HCC model code (None if not HCC-relevant)
    raf_weight = Column(Float, nullable=True)           # CMS RAF weight for this HCC code
    clinical_status = Column(String(30), nullable=False, default="active")
    onset_date = Column(String(10), nullable=True)      # ISO-8601
    fhir_json = Column(Text, nullable=False)            # Raw validated FHIR R4 JSON

    patient = relationship("Patient", back_populates="conditions")

    def __repr__(self) -> str:
        return f"<Condition {self.icd10_code} HCC={self.hcc_code} RAF={self.raf_weight}>"


class ClinicalNote(Base):
    """FHIR DocumentReference — unstructured clinical notes containing the HCC evidence."""

    __tablename__ = "clinical_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    fhir_id = Column(String(64), unique=True, nullable=False)
    note_type = Column(String(80), nullable=False)     # e.g. "Office Visit Note"
    content = Column(Text, nullable=False)             # Full plain-text note
    authored_date = Column(String(10), nullable=False) # ISO-8601
    author = Column(String(120), nullable=True)
    fhir_json = Column(Text, nullable=False)

    patient = relationship("Patient", back_populates="clinical_notes")

    def __repr__(self) -> str:
        return f"<ClinicalNote type={self.note_type!r} on {self.authored_date!r}>"
