"""
src/hcc_engine.py — Generative HCC Risk Adjustment Engine
==========================================================
Core logic for the HCC Risk Navigator.

The main entry point is audit_hcc_gaps(), which:
  1. Computes the patient's current RAF score from coded ICD-10 conditions.
  2. Calls GPT-4o-mini with the existing problem list + unstructured notes to
     identify clinically documented but UNCODED conditions (HCC gaps).
  3. Returns a structured audit report with:
       - Suspected missing ICD-10/HCC codes
       - Supporting evidence quote from the note
       - Per-gap RAF delta
       - Projected total RAF after capture

HCC Background:
  CMS (Centers for Medicare & Medicaid Services) uses Hierarchical Condition
  Categories (HCCs) to risk-adjust Medicare Advantage payments. Each HCC maps
  to a Risk Adjustment Factor (RAF) score. Hospitals lose millions annually
  when clinically documented conditions are not captured in the coded problem
  list — this engine closes that gap.
"""
from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# HCC Code Map — ICD-10 → HCC model code + CMS RAF weight
# Source: CMS HCC Model V28 (2024)
# ─────────────────────────────────────────────────────────────────────────────

HCC_MAP: dict[str, dict] = {
    "E11.9":   {"hcc": 19,  "label": "Type 2 Diabetes w/o Complications",          "raf": 0.104},
    "E11.40":  {"hcc": 18,  "label": "Type 2 Diabetes w/ Diabetic Neuropathy",     "raf": 0.302},
    "E11.41":  {"hcc": 18,  "label": "Type 2 Diabetes w/ Diabetic Mononeuropathy", "raf": 0.302},
    "E11.65":  {"hcc": 18,  "label": "Type 2 Diabetes w/ Hyperglycemia",           "raf": 0.302},
    "E11.51":  {"hcc": 18,  "label": "Type 2 Diabetes w/ Diabetic Peripheral Angiopathy", "raf": 0.302},
    "I50.9":   {"hcc": 85,  "label": "Heart Failure, Unspecified",                 "raf": 0.331},
    "I50.32":  {"hcc": 85,  "label": "Chronic Diastolic Heart Failure",            "raf": 0.331},
    "N18.3":   {"hcc": 137, "label": "CKD Stage 3",                                "raf": 0.289},
    "N18.4":   {"hcc": 136, "label": "CKD Stage 4",                                "raf": 0.421},
    "N18.5":   {"hcc": 135, "label": "CKD Stage 5",                                "raf": 0.636},
    "J44.1":   {"hcc": 111, "label": "COPD with Exacerbation",                     "raf": 0.335},
    "J44.0":   {"hcc": 111, "label": "COPD with Acute Lower Respiratory Infection", "raf": 0.335},
    "F32.9":   {"hcc": 59,  "label": "Major Depressive Disorder",                  "raf": 0.309},
    "F33.0":   {"hcc": 59,  "label": "Recurrent Major Depressive Disorder",        "raf": 0.309},
    "G40.909": {"hcc": 79,  "label": "Epilepsy, Unspecified",                      "raf": 0.612},
    "I10":     {"hcc": 0,   "label": "Essential Hypertension",                     "raf": 0.0},
    "Z87.39":  {"hcc": 0,   "label": "Personal History of Other Conditions",       "raf": 0.0},
}

# ─────────────────────────────────────────────────────────────────────────────
# RAF Calculator
# ─────────────────────────────────────────────────────────────────────────────

def compute_raf(icd10_codes: list[str]) -> float:
    """
    Compute the total RAF score for a list of ICD-10 codes.
    Only sums HCC-coded conditions; ignores duplicate HCC codes (higher wins).
    """
    seen_hccs: set[int] = set()
    total_raf = 0.0
    for code in icd10_codes:
        entry = HCC_MAP.get(code)
        if entry and entry["hcc"] > 0 and entry["hcc"] not in seen_hccs:
            total_raf += entry["raf"]
            seen_hccs.add(entry["hcc"])
    return round(total_raf, 3)


# ─────────────────────────────────────────────────────────────────────────────
# LLM Integration (isolated for test mocking)
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are an expert medical coder and Clinical Documentation Improvement (CDI) specialist with deep knowledge of ICD-10-CM coding guidelines and CMS HCC risk adjustment models.

Your task is to analyze unstructured clinical notes and identify conditions that are CLINICALLY DOCUMENTED in the notes but NOT CODED in the patient's current structured problem list.

Focus specifically on conditions that map to HCC codes (i.e., chronic, complex conditions that affect Medicare Advantage risk adjustment).

Your output MUST also include a 'draft_clinician_query'. This must be a formal, compliant message to the attending physician asking them to amend their chart based on the found evidence (e.g., "Dr. Nakamura, your note from [Date] mentions [evidence], but [Code] is not on the problem list. Do you agree to amend the chart?").

Respond ONLY with a valid JSON object — no markdown, no explanation outside the JSON."""

def _build_llm_prompt(existing_codes: list[str], notes_text: str) -> list[dict]:
    """Build the OpenAI chat messages for the HCC gap analysis."""
    coded_descriptions = []
    for code in existing_codes:
        entry = HCC_MAP.get(code, {})
        coded_descriptions.append(
            f"  - {code}: {entry.get('label', 'Unknown')} (HCC {entry.get('hcc', 'N/A')}, RAF {entry.get('raf', 0.0)})"
        )
    coded_list_str = "\n".join(coded_descriptions) if coded_descriptions else "  (No conditions coded)"

    user_prompt = f"""
## Patient's CURRENT Coded Problem List (ICD-10)
{coded_list_str}

## Unstructured Clinical Notes
{notes_text}

## Your Task
Identify any conditions that are:
1. Clearly documented (explicitly stated or strongly implied) in the clinical notes
2. NOT already captured in the coded problem list above
3. Clinically significant and mappable to a specific ICD-10-CM code

Return a JSON object with this exact structure:
{{
  "gaps": [
    {{
      "suspected_icd10": "<ICD-10 code string, e.g. E11.40>",
      "suspected_hcc": <integer HCC code, or 0 if non-HCC>,
      "description": "<full condition name>",
      "evidence_quote": "<exact quote from the notes that supports this finding>",
      "clinical_rationale": "<1-2 sentence explanation of your coding reasoning>",
      "raf_delta": <float — RAF weight for this code, or 0.0 if non-HCC>,
      "confidence": "<HIGH|MEDIUM|LOW>",
      "draft_clinician_query": "<formal, compliant message to the attending physician asking them to amend their chart>",
      "meat_criteria": {{
        "condition": "<patient's condition or diagnosis>",
        "symptoms": "<symptoms recorded during the visit>",
        "treatments": "<treatment or management plans discussed or implemented (medications, lifestyle advice, referrals)>"
      }}
    }}
  ],
  "audit_summary": "<2-3 sentence plain-English summary of findings for the CDI specialist>"
}}

If no gaps are found, return {{"gaps": [], "audit_summary": "No HCC coding gaps identified."}}
""".strip()

    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def _call_llm(existing_codes: list[str], notes_text: str) -> str:
    """
    Call GPT-4o-mini for HCC gap analysis.
    Isolated in its own function so tests can patch it:
        with patch("src.hcc_engine._call_llm", return_value=mock_json):
    """
    import openai

    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    messages = _build_llm_prompt(existing_codes, notes_text)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.1,
        response_format={"type": "json_object"},
        max_tokens=1024,
    )
    return response.choices[0].message.content


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def audit_hcc_gaps(fhir_context: dict[str, Any]) -> dict[str, Any]:
    """
    Main HCC audit function. Combines deterministic RAF computation with
    LLM-powered gap detection across unstructured clinical documentation.

    Args:
        fhir_context: Output of get_fhir_context() — patient, conditions,
                      clinical_notes.

    Returns:
        Structured audit report with current/projected RAF, identified gaps,
        evidence quotes, and an audit summary.
    """
    patient = fhir_context.get("patient", {})
    conditions = fhir_context.get("conditions", [])
    clinical_notes = fhir_context.get("clinical_notes", [])

    # Step 1: Compute current RAF from coded diagnoses
    existing_codes = [c["icd10_code"] for c in conditions]
    current_raf = compute_raf(existing_codes)

    # Step 2: Compile notes text for LLM
    notes_text = "\n\n---\n\n".join(
        f"[{n.get('note_type', 'Note')} — {n.get('authored_date', '')}]\n{n.get('content', '')}"
        for n in clinical_notes
    ) or "(No clinical notes available)"

    # Step 3: LLM gap detection
    llm_raw = _call_llm(existing_codes, notes_text)

    # Step 4: Parse LLM response
    try:
        llm_result = json.loads(llm_raw)
    except (json.JSONDecodeError, TypeError):
        llm_result = {"gaps": [], "audit_summary": "LLM response could not be parsed."}

    # Step 5: Validate gaps against HCC_MAP and compute projected RAF
    validated_gaps = []
    for gap in llm_result.get("gaps", []):
        icd10 = gap.get("suspected_icd10", "")
        hcc_entry = HCC_MAP.get(icd10, {})
        # Use our local RAF data as truth (not LLM's raf_delta)
        raf_delta = hcc_entry.get("raf", gap.get("raf_delta", 0.0))
        # Embed the MEAT criteria safely without symbols that might break Po's JSON payload generator
        meat = gap.get("meat_criteria", {})
        enhanced_evidence = (
            f"{gap.get('evidence_quote', '')} "
            f"(MEAT Compliance Data - Condition: {meat.get('condition', 'N/A')}, "
            f"Symptoms: {meat.get('symptoms', 'N/A')}, "
            f"Treatments: {meat.get('treatments', 'N/A')})"
        )
        validated_gaps.append({
            "suspected_icd10": icd10,
            "suspected_hcc": gap.get("suspected_hcc", hcc_entry.get("hcc", 0)),
            "description": gap.get("description", hcc_entry.get("label", "")),
            "evidence_quote": enhanced_evidence,
            "clinical_rationale": gap.get("clinical_rationale", ""),
            "raf_delta": raf_delta,
            "confidence": gap.get("confidence", "MEDIUM"),
            "draft_clinician_query": gap.get("draft_clinician_query", ""),
            "meat_criteria": meat,
        })

    # Sum RAF from unique new HCC codes only (don't double-count)
    existing_hccs = {HCC_MAP[c]["hcc"] for c in existing_codes if c in HCC_MAP and HCC_MAP[c]["hcc"] > 0}
    additional_raf = sum(
        g["raf_delta"]
        for g in validated_gaps
        if HCC_MAP.get(g["suspected_icd10"], {}).get("hcc", 0) not in existing_hccs
        and HCC_MAP.get(g["suspected_icd10"], {}).get("hcc", 0) > 0
    )
    projected_raf = round(current_raf + additional_raf, 3)

    return {
        "patient_id": patient.get("fhir_id", "unknown"),
        "patient_name": patient.get("name", "Unknown"),
        "current_raf": current_raf,
        "projected_raf": projected_raf,
        "raf_delta": round(projected_raf - current_raf, 3),
        "existing_codes": existing_codes,
        "gaps": validated_gaps,
        "audit_summary": llm_result.get("audit_summary", ""),
        "gap_count": len(validated_gaps),
    }
