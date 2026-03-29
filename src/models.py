"""
SQLAlchemy ORM models for the Mock EHR database.
Each record stores both structured fields AND the raw FHIR R4 JSON blob.
"""
from __future__ import annotations

import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Patient(Base):
    """Core patient demographics record."""

    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fhir_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    dob = Column(String(10), nullable=False)          # ISO-8601 date string
    gender = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    medications = relationship("MedicationRequest", back_populates="patient", cascade="all, delete-orphan")
    observations = relationship("Observation", back_populates="patient", cascade="all, delete-orphan")
    clinical_notes = relationship("ClinicalNote", back_populates="patient", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Patient id={self.fhir_id} name={self.name!r}>"


class MedicationRequest(Base):
    """FHIR MedicationRequest — one row per prescription episode."""

    __tablename__ = "medication_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    fhir_id = Column(String(64), unique=True, nullable=False)
    medication_name = Column(String(120), nullable=False)
    dosage = Column(String(80), nullable=True)
    start_date = Column(String(10), nullable=False)   # ISO-8601
    end_date = Column(String(10), nullable=True)       # ISO-8601 or NULL if ongoing
    status = Column(String(40), nullable=False, default="completed")
    fhir_json = Column(Text, nullable=False)           # Raw validated FHIR R4 JSON

    patient = relationship("Patient", back_populates="medications")

    def __repr__(self) -> str:
        return f"<MedicationRequest {self.medication_name} [{self.start_date}→{self.end_date}]>"


class Observation(Base):
    """FHIR Observation — lab results and vitals."""

    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    fhir_id = Column(String(64), unique=True, nullable=False)
    loinc_code = Column(String(20), nullable=False)    # e.g., "4548-4" for A1C
    display = Column(String(120), nullable=False)      # Human-readable name
    value = Column(Float, nullable=False)
    unit = Column(String(30), nullable=False)
    effective_date = Column(String(10), nullable=False)
    fhir_json = Column(Text, nullable=False)

    patient = relationship("Patient", back_populates="observations")

    def __repr__(self) -> str:
        return f"<Observation {self.display}={self.value}{self.unit} on {self.effective_date}>"


class ClinicalNote(Base):
    """FHIR DocumentReference — unstructured clinical notes."""

    __tablename__ = "clinical_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    fhir_id = Column(String(64), unique=True, nullable=False)
    note_type = Column(String(80), nullable=False)     # e.g., "Progress Note"
    content = Column(Text, nullable=False)             # Full plain-text note
    authored_date = Column(String(10), nullable=False)
    author = Column(String(120), nullable=True)
    fhir_json = Column(Text, nullable=False)

    patient = relationship("Patient", back_populates="clinical_notes")

    def __repr__(self) -> str:
        return f"<ClinicalNote type={self.note_type!r} on {self.authored_date}>"
