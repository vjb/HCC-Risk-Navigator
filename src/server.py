"""
src/server.py — FastAPI + MCP Server
=====================================
Exposes the Auto-Auth Pre-Cog Engine as an MCP (Model Context Protocol) server
using HTTP/SSE transport (Streamable HTTP) for integration with Prompt Opinion
and ngrok tunneling.

Three MCP tools are exposed:
  - get_fhir_context(patient_id)         → Full FHIR context from Mock EHR
  - hunt_clinical_evidence(patient_id, condition_keyword) → Matching clinical notes
  - generate_pa_justification(patient_id, target_medication, policy_text) → PA analysis

REST endpoints (for easy testing via HTTPX):
  GET  /health                            → Health check
  POST /tools/get_fhir_context            → Direct REST access to the MCP tool
  POST /tools/hunt_clinical_evidence      → Direct REST access
  POST /tools/generate_pa_justification   → Direct REST access

MCP endpoint:
  /mcp                                    → MCP SSE transport (for Prompt Opinion)
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("auto-auth-mcp")

# ─────────────────────────────────────────────────────────────────────────────
# Database bootstrap
# ─────────────────────────────────────────────────────────────────────────────

from src.database import get_session, init_db
from src.models import ClinicalNote, MedicationRequest, Observation, Patient
from src.pa_engine import generate_pa_analysis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB tables on startup."""
    logger.info("🚀 Auto-Auth Pre-Cog MCP Server starting up...")
    init_db()
    logger.info("✅ Database initialized.")
    yield
    logger.info("🛑 Server shutting down.")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI Application
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Auto-Auth Pre-Cog Engine",
    description=(
        "FHIR-native MCP server providing Generative AI Prior Authorization "
        "reasoning. Exposes get_fhir_context, hunt_clinical_evidence, and "
        "generate_pa_justification tools for Prompt Opinion integration."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────────────────────────────────────

class GetFhirContextRequest(BaseModel):
    patient_id: str


class HuntClinicalEvidenceRequest(BaseModel):
    patient_id: str
    condition_keyword: str


class GeneratePAJustificationRequest(BaseModel):
    patient_id: str
    target_medication: str
    policy_text: str


# ─────────────────────────────────────────────────────────────────────────────
# Core Tool Logic (shared by REST endpoints and MCP tools)
# ─────────────────────────────────────────────────────────────────────────────

def _get_patient_or_404(session, patient_id: str) -> Patient:
    """Look up patient by FHIR ID or raise HTTP 404."""
    patient = session.query(Patient).filter_by(fhir_id=patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=404,
            detail=f"Patient with FHIR ID '{patient_id}' not found in Mock EHR.",
        )
    return patient


def _build_fhir_context(patient: Patient, session) -> dict[str, Any]:
    """Construct the full FHIR context dict from ORM objects."""
    medications = session.query(MedicationRequest).filter_by(patient_id=patient.id).all()
    observations = session.query(Observation).filter_by(patient_id=patient.id).all()
    notes = session.query(ClinicalNote).filter_by(patient_id=patient.id).all()

    return {
        "patient": {
            "fhir_id": patient.fhir_id,
            "name": patient.name,
            "dob": patient.dob,
            "gender": patient.gender,
        },
        "medications": [
            {
                "medication_name": m.medication_name,
                "dosage": m.dosage,
                "start_date": m.start_date,
                "end_date": m.end_date,
                "status": m.status,
                "fhir_json": m.fhir_json,
            }
            for m in medications
        ],
        "observations": [
            {
                "loinc_code": o.loinc_code,
                "display": o.display,
                "value": o.value,
                "unit": o.unit,
                "effective_date": o.effective_date,
            }
            for o in observations
        ],
        "clinical_notes": [
            {
                "note_type": n.note_type,
                "content": n.content,
                "authored_date": n.authored_date,
                "author": n.author,
            }
            for n in notes
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# REST Endpoints (primary interface for testing + REST clients)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check endpoint for uptime monitoring and load balancers."""
    return {"status": "ok", "service": "Auto-Auth Pre-Cog Engine", "version": "0.1.0"}


@app.post("/tools/get_fhir_context")
async def tool_get_fhir_context(request: GetFhirContextRequest):
    """
    MCP Tool: get_fhir_context
    Returns the full FHIR context for a patient (demographics, medications,
    observations, clinical notes) from the Mock EHR SQLite database.
    
    SHARP Extension: Accepts patient_id propagated from the Prompt Opinion platform.
    """
    logger.info(f"🔍 get_fhir_context called for patient_id={request.patient_id!r}")
    session = get_session()
    try:
        patient = _get_patient_or_404(session, request.patient_id)
        context = _build_fhir_context(patient, session)
        logger.info(
            f"✅ Returning FHIR context: "
            f"{len(context['medications'])} meds, "
            f"{len(context['observations'])} obs, "
            f"{len(context['clinical_notes'])} notes"
        )
        return context
    finally:
        session.close()


@app.post("/tools/hunt_clinical_evidence")
async def tool_hunt_clinical_evidence(request: HuntClinicalEvidenceRequest):
    """
    MCP Tool: hunt_clinical_evidence
    Searches clinical notes for a given condition keyword (case-insensitive).
    Returns a list of matching notes with excerpts.
    
    SHARP Extension: Accepts patient_id and condition_keyword from the orchestrating agent.
    """
    logger.info(
        f"🩺 hunt_clinical_evidence called: "
        f"patient={request.patient_id!r}, keyword={request.condition_keyword!r}"
    )
    session = get_session()
    try:
        patient = _get_patient_or_404(session, request.patient_id)
        notes = session.query(ClinicalNote).filter_by(patient_id=patient.id).all()

        keyword_lower = request.condition_keyword.lower()
        matching = [
            {
                "note_type": n.note_type,
                "authored_date": n.authored_date,
                "author": n.author,
                "content": n.content,
                "excerpt": n.content[:300] + "..." if len(n.content) > 300 else n.content,
            }
            for n in notes
            if keyword_lower in n.content.lower()
        ]

        logger.info(f"🔎 Found {len(matching)} matching notes for keyword={request.condition_keyword!r}")
        return {
            "patient_id": request.patient_id,
            "keyword": request.condition_keyword,
            "matching_notes": matching,
            "total_notes_searched": len(notes),
        }
    finally:
        session.close()


@app.post("/tools/generate_pa_justification")
async def tool_generate_pa_justification(request: GeneratePAJustificationRequest):
    """
    MCP Tool: generate_pa_justification
    Triggers the full AI Prior Authorization reasoning pipeline:
      1. Loads FHIR context from Mock EHR.
      2. Runs deterministic step-therapy + clinical evidence analysis.
      3. Calls GPT-4o-mini to validate and draft the PA exception letter.
    Returns a complete structured PA analysis payload.
    
    SHARP Extension: Accepts patient_id, target_medication, and policy_text from the agent.
    """
    logger.info(
        f"⚕️ generate_pa_justification called: "
        f"patient={request.patient_id!r}, medication={request.target_medication!r}"
    )
    session = get_session()
    try:
        patient = _get_patient_or_404(session, request.patient_id)
        fhir_context = _build_fhir_context(patient, session)

        result = generate_pa_analysis(
            fhir_context=fhir_context,
            target_medication=request.target_medication,
            policy_text=request.policy_text,
        )

        logger.info(
            f"📋 PA analysis complete: "
            f"step_therapy_met={result['step_therapy_met']}, "
            f"exception_found={result['exception_found']}"
        )
        return result
    finally:
        session.close()


# ─────────────────────────────────────────────────────────────────────────────
# MCP SSE Transport (for Prompt Opinion integration)
# ─────────────────────────────────────────────────────────────────────────────

try:
    from mcp.server.fastmcp import FastMCP
    from mcp.server.transport_security import TransportSecuritySettings

    # Disable DNS rebinding protection for local dev/test.
    # Production ngrok tunnels use real HTTPS hostnames (valid Host headers).
    # ASGI test clients use 'localhost' which the default MCP security rejects,
    # so we disable the check globally for this local server.
    _transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    )

    mcp_server = FastMCP(
        name="auto-auth-pre-cog",
        instructions=(
            "Prior Authorization AI Engine. Use get_fhir_context to retrieve "
            "patient records, hunt_clinical_evidence to find exception evidence, "
            "and generate_pa_justification to produce a complete PA analysis."
        ),
    )
    mcp_server.settings.transport_security = _transport_security

    @mcp_server.tool()
    async def get_fhir_context(patient_id: str) -> dict:
        """
        Retrieve full FHIR R4 context for a patient from the Mock EHR.
        Returns demographics, medication history, lab observations, and clinical notes.
        """
        session = get_session()
        try:
            patient = session.query(Patient).filter_by(fhir_id=patient_id).first()
            if not patient:
                return {"error": f"Patient '{patient_id}' not found"}
            return _build_fhir_context(patient, session)
        finally:
            session.close()

    @mcp_server.tool()
    async def hunt_clinical_evidence(patient_id: str, condition_keyword: str) -> dict:
        """
        Search clinical notes for evidence of a specific condition or adverse reaction.
        Use this to find documented exceptions to step-therapy requirements.
        """
        session = get_session()
        try:
            patient = session.query(Patient).filter_by(fhir_id=patient_id).first()
            if not patient:
                return {"error": f"Patient '{patient_id}' not found", "matching_notes": []}
            notes = session.query(ClinicalNote).filter_by(patient_id=patient.id).all()
            keyword_lower = condition_keyword.lower()
            matching = [
                {
                    "note_type": n.note_type,
                    "authored_date": n.authored_date,
                    "content": n.content,
                }
                for n in notes if keyword_lower in n.content.lower()
            ]
            return {"patient_id": patient_id, "keyword": condition_keyword, "matching_notes": matching}
        finally:
            session.close()

    @mcp_server.tool()
    async def generate_pa_justification(
        patient_id: str,
        target_medication: str,
        policy_text: str,
    ) -> dict:
        """
        Generate a complete Prior Authorization analysis including step-therapy assessment,
        clinical exception evaluation, and a drafted PA exception letter ready for submission.
        """
        session = get_session()
        try:
            patient = session.query(Patient).filter_by(fhir_id=patient_id).first()
            if not patient:
                return {"error": f"Patient '{patient_id}' not found"}
            fhir_context = _build_fhir_context(patient, session)
            return generate_pa_analysis(
                fhir_context=fhir_context,
                target_medication=target_medication,
                policy_text=policy_text,
            )
        finally:
            session.close()

    # Mount MCP SSE transport at /mcp
    # sse_app() exposes:
    #   GET  /mcp/sse       → text/event-stream (Prompt Opinion connects here)
    #   POST /mcp/messages  → JSON-RPC 2.0 message bus (Prompt Opinion POSTs here)
    mcp_app = mcp_server.sse_app()
    app.mount("/mcp", mcp_app)
    logger.info("✅ MCP SSE transport mounted at /mcp/sse and /mcp/messages")

except ImportError as e:
    logger.warning(f"⚠️  MCP SDK not available ({e}). REST endpoints still active.")


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_SERVER_PORT", "8000"))

    print(f"\n🚀 Auto-Auth Pre-Cog MCP Server")
    print(f"   REST API  → http://{host}:{port}")
    print(f"   MCP/SSE   → http://{host}:{port}/mcp")
    print(f"   Health    → http://{host}:{port}/health")
    print(f"   Docs      → http://{host}:{port}/docs\n")

    uvicorn.run(
        "src.server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info",
    )
