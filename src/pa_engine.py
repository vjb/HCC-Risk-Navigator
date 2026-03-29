"""
src/pa_engine.py — Generative AI Prior Authorization Reasoning Engine
======================================================================
Core logic for the Auto-Auth Pre-Cog Engine.

The main entry point is generate_pa_analysis(), which:
  1. Parses the FHIR context (medications, observations, notes) locally.
  2. Computes step-therapy compliance deterministically (no LLM for this).
  3. Scans clinical notes for exception evidence (keyword-seeded, then LLM-confirmed).
  4. Calls GPT-4o-mini with a highly structured prompt to:
       a. Validate the step-therapy assessment.
       b. Evaluate evidence quality.
       c. Draft a complete PA exception request letter.
  5. Returns a structured dict ready for the MCP tool response.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

# Number of days of prior therapy required by the policy (Aetna default: 6 months)
DEFAULT_REQUIRED_DAYS = 180

# Exception keywords to scan for in clinical notes (case-insensitive)
EXCEPTION_KEYWORDS = [
    "gi intolerance",
    "gastrointestinal",
    "intolerance",
    "adverse reaction",
    "adverse effect",
    "contraindication",
    "contraindicated",
    "lactic acidosis",
    "renal impairment",
    "discontinued",
    "discontinue",
    "unable to tolerate",
    "cannot tolerate",
    "severe nausea",
    "severe diarrhea",
]


# ─────────────────────────────────────────────────────────────────────────────
# Data types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StepTherapyResult:
    """Structured output of the local (non-LLM) step therapy analysis."""
    met: bool
    duration_days: int
    required_days: int
    prior_drug: str | None
    notes: str


# ─────────────────────────────────────────────────────────────────────────────
# Local (Deterministic) Analysis
# ─────────────────────────────────────────────────────────────────────────────

def _compute_step_therapy(
    medications: list[dict],
    target_medication: str,
    required_days: int = DEFAULT_REQUIRED_DAYS,
) -> StepTherapyResult:
    """
    Evaluate whether the patient has completed sufficient prior therapy.
    Looks for the longest completed course of any medication that isn't
    the target medication itself.

    Returns a StepTherapyResult with .met indicating compliance.
    """
    target_lower = target_medication.lower()
    longest_days = 0
    prior_drug = None

    for med in medications:
        name = med.get("medication_name", "")
        # Skip current target drug
        if any(kw in name.lower() for kw in ["ozempic", "semaglutide", "wegovy", "rybelsus"]):
            if any(kw in target_lower for kw in ["ozempic", "semaglutide"]):
                continue

        start_str = med.get("start_date")
        end_str = med.get("end_date")
        if not start_str:
            continue

        try:
            start = date.fromisoformat(start_str)
            end = date.fromisoformat(end_str) if end_str else date.today()
        except (ValueError, TypeError):
            continue

        duration = (end - start).days
        if duration > longest_days:
            longest_days = duration
            prior_drug = name

    met = longest_days >= required_days
    note = (
        f"Longest qualifying prior therapy: {longest_days} days of {prior_drug or 'unknown'}. "
        f"Policy requires {required_days} days. "
        f"{'REQUIREMENT MET.' if met else 'REQUIREMENT NOT MET — step therapy deficient.'}"
    )
    return StepTherapyResult(
        met=met,
        duration_days=longest_days,
        required_days=required_days,
        prior_drug=prior_drug,
        notes=note,
    )


def _extract_exception_evidence(clinical_notes: list[dict]) -> tuple[bool, str]:
    """
    Scan clinical notes for known exception keywords.
    Returns (found: bool, evidence_snippet: str).
    """
    matched_notes = []
    for note in clinical_notes:
        content = note.get("content", "").lower()
        hit_keywords = [kw for kw in EXCEPTION_KEYWORDS if kw in content]
        if hit_keywords:
            matched_notes.append({
                "note_type": note.get("note_type", "Clinical Note"),
                "authored_date": note.get("authored_date", ""),
                "matched_keywords": hit_keywords,
                "excerpt": note.get("content", "")[:500],  # First 500 chars
            })

    if not matched_notes:
        return False, ""

    # Build a concise evidence summary for the LLM prompt
    evidence_parts = []
    for n in matched_notes:
        evidence_parts.append(
            f"[{n['note_type']} dated {n['authored_date']}] "
            f"Keywords detected: {', '.join(n['matched_keywords'])}. "
            f"Excerpt: {n['excerpt'][:200]}..."
        )

    return True, "\n\n".join(evidence_parts)


# ─────────────────────────────────────────────────────────────────────────────
# LLM Integration
# ─────────────────────────────────────────────────────────────────────────────

def _build_llm_prompt(
    patient: dict,
    step_therapy: StepTherapyResult,
    exception_evidence: str,
    target_medication: str,
    policy_text: str,
) -> list[dict]:
    """Build the OpenAI chat messages list for the PA reasoning call."""
    system_prompt = (
        "You are an expert clinical pharmacist and prior authorization specialist. "
        "Your task is to analyze a patient's medication history against insurance policy "
        "requirements and produce a structured prior authorization assessment. "
        "You must be clinically accurate, legally precise, and advocate strongly for the "
        "patient when there is legitimate clinical evidence supporting an exception. "
        "Always respond with valid JSON only — no markdown, no explanation outside JSON."
    )

    patient_summary = (
        f"Patient: {patient.get('name', 'Unknown')} "
        f"(DOB: {patient.get('dob', 'N/A')}, Gender: {patient.get('gender', 'N/A')})\n"
        f"FHIR ID: {patient.get('fhir_id', 'N/A')}"
    )

    user_prompt = f"""
Analyze the following prior authorization case and respond with a JSON object.

## Patient Information
{patient_summary}

## Step Therapy Assessment (Computed Locally)
{step_therapy.notes}
- Duration completed: {step_therapy.duration_days} days
- Duration required: {step_therapy.required_days} days
- Step therapy met: {step_therapy.met}
- Prior drug: {step_therapy.prior_drug or 'Unknown'}

## Target Medication Requested
{target_medication}

## Insurance Policy Text
{policy_text}

## Clinical Exception Evidence Found in Notes
{exception_evidence if exception_evidence else "No exception keywords detected in clinical notes."}

## Your Task
Return ONLY a JSON object with these exact keys:
{{
  "step_therapy_assessment": "<string: detailed assessment of step therapy compliance>",
  "exception_found": <true|false: whether a valid clinical exception exists>,
  "exception_evidence": "<string: summary of the clinical evidence supporting the exception, or empty string>",
  "pa_letter": "<string: complete, professional PA exception request letter ready for submission>"
}}

The pa_letter must:
- Be addressed to the insurance company's Prior Authorization Department
- Include patient name, DOB, and target medication
- State the step therapy status clearly
- Cite the specific clinical exception with exact quotes from the notes
- Request approval of the target medication
- Be signed by the treating physician (Dr. Sarah Morrison, MD)
- Use professional medical-legal language appropriate for insurance submission
"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt.strip()},
    ]


def _call_llm(messages: list[dict]) -> str:
    """
    Call OpenAI GPT-4o-mini and return the raw content string.
    This function is intentionally isolated so tests can mock it easily:
        with patch("src.pa_engine._call_llm", return_value=mock_json):
    """
    import openai

    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.2,              # Low temperature for consistent, factual output
        response_format={"type": "json_object"},
        max_tokens=2048,
    )
    return response.choices[0].message.content


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def generate_pa_analysis(
    fhir_context: dict,
    target_medication: str,
    policy_text: str,
    required_days: int = DEFAULT_REQUIRED_DAYS,
) -> dict[str, Any]:
    """
    Main PA reasoning function. Combines deterministic FHIR analysis with
    LLM-powered exception evaluation and letter drafting.

    Args:
        fhir_context: Output from get_fhir_context() — patient, medications,
                      observations, clinical_notes.
        target_medication: The drug being requested (e.g., "Ozempic").
        policy_text: Raw insurance policy text for the target drug.
        required_days: Minimum prior therapy duration (default 180 = 6 months).

    Returns:
        Dict with keys: step_therapy_met, exception_found, exception_evidence,
        pa_letter, therapy_duration_days, required_duration_days, target_medication.
    """
    patient = fhir_context.get("patient", {})
    medications = fhir_context.get("medications", [])
    clinical_notes = fhir_context.get("clinical_notes", [])

    # Step 1: Local deterministic step-therapy check
    step_therapy = _compute_step_therapy(medications, target_medication, required_days)

    # Step 2: Local keyword-based exception evidence scan
    exception_found_local, exception_evidence = _extract_exception_evidence(clinical_notes)

    # Step 3: Build LLM prompt and call the model
    messages = _build_llm_prompt(
        patient=patient,
        step_therapy=step_therapy,
        exception_evidence=exception_evidence,
        target_medication=target_medication,
        policy_text=policy_text,
    )
    llm_raw = _call_llm(messages)

    # Step 4: Parse LLM response (validated JSON)
    try:
        llm_result = json.loads(llm_raw)
    except (json.JSONDecodeError, TypeError):
        # Fallback: use local analysis if LLM returns malformed JSON
        llm_result = {
            "step_therapy_assessment": step_therapy.notes,
            "exception_found": exception_found_local,
            "exception_evidence": exception_evidence,
            "pa_letter": "Unable to generate PA letter — LLM response was malformed.",
        }

    # Step 5: Merge local analysis with LLM results (local truth overrides on key fields)
    return {
        "step_therapy_met": step_therapy.met,          # Always from local deterministic logic
        "exception_found": bool(llm_result.get("exception_found", exception_found_local)),
        "exception_evidence": llm_result.get("exception_evidence", exception_evidence),
        "pa_letter": llm_result.get("pa_letter", ""),
        "step_therapy_assessment": llm_result.get("step_therapy_assessment", step_therapy.notes),
        "therapy_duration_days": step_therapy.duration_days,
        "required_duration_days": required_days,
        "target_medication": target_medication,
        "prior_drug": step_therapy.prior_drug,
    }
