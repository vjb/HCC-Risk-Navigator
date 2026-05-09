"""
src/hcc_engine.py — Deterministic HCC Risk Adjustment Engine
=============================================================
Entry points:
  audit_hcc_gaps()  — pure FHIR data extraction + RAF computation.
                      NO LLM CALLS. Returns structured clinical context
                      for Po's agent to perform CDI gap analysis.
  format_5ts()      — scaffolds the 5Ts deliverable framework from audit output.

Design principle:
  This engine is a FHIR data pipeline and RAF calculator only. The intelligence
  (identifying uncoded conditions from clinical notes) lives in the Po agent LLM,
  which has full conversation context and access to the structured data this
  engine returns. This avoids the need for a separate OpenAI key and keeps
  all LLM work on the Prompt Opinion platform.

HCC Background:
  CMS (Centers for Medicare & Medicaid Services) uses Hierarchical Condition
  Categories (HCCs) to risk-adjust Medicare Advantage payments. Each HCC maps
  to a Risk Adjustment Factor (RAF) score. Hospitals lose millions annually
  when clinically documented conditions are not captured in the coded problem
  list — this engine surfaces that gap for Po's agent to act on.

V28 Revenue Context:
  In 2026, CMS completed the transition from HCC Model V24 to V28.
  'Unspecified' codes (e.g. E11.9 → E11.40) that were valid in V24 now map
  to lower or zero reimbursement. The revenue cliff is real and immediate.
"""
from __future__ import annotations

import json
from typing import Any


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
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def audit_hcc_gaps(fhir_context: dict[str, Any]) -> dict[str, Any]:
    """
    Deterministic FHIR data extraction and RAF computation.

    No LLM calls are made here. This function:
      1. Extracts and computes the patient's current RAF from coded ICD-10 conditions.
      2. Compiles all clinical note text into a single reviewable string.
      3. Packages the full HCC V28 reference table as context.
      4. Returns a structured clinical context payload for Po's agent to:
            - Identify conditions documented in notes but missing from the problem list
            - Map findings to ICD-10 codes using hcc_reference_v28
            - Quantify the revenue impact of each gap
            - Generate the 5Ts deliverables (Table, Template, Task, Talk)

    Args:
        fhir_context: Output of _fetch_fhir_patient_context() or _build_fhir_context()
                      — contains patient, conditions, clinical_notes.

    Returns:
        Structured audit context. The 'gaps' list is always empty from this
        function — Po's agent populates it through CDI analysis of clinical_notes_text.
    """
    patient    = fhir_context.get("patient", {})
    conditions = fhir_context.get("conditions", [])
    clinical_notes = fhir_context.get("clinical_notes", [])

    # ── Step 1: Extract coded ICD-10 diagnoses ───────────────────────────────
    existing_codes: list[str] = []
    coded_conditions_detail: list[dict] = []

    for c in conditions:
        coding = c.get("code", {}).get("coding", [])
        for code_entry in coding:
            icd10 = code_entry.get("code", "")
            if icd10:
                existing_codes.append(icd10)
                hcc_info = HCC_MAP.get(icd10, {})
                coded_conditions_detail.append({
                    "icd10":       icd10,
                    "description": code_entry.get("display", hcc_info.get("label", "Unknown")),
                    "hcc_code":    hcc_info.get("hcc", None),
                    "raf_weight":  hcc_info.get("raf", 0.0),
                    "in_hcc_v28":  icd10 in HCC_MAP,
                })

    current_raf = compute_raf(existing_codes)

    # ── Step 2: Compile clinical notes for agent review ──────────────────────
    notes_parts: list[str] = []
    for n in clinical_notes:
        note_type    = n.get("type", {}).get("text", "Note")
        date         = n.get("date", "")
        author_list  = n.get("author", [])
        author       = author_list[0].get("display", "Unknown") if author_list else "Unknown"
        content_text = ""
        contents = n.get("content", [])
        if contents:
            content_text = contents[0].get("attachment", {}).get("data", "")
        if content_text:
            notes_parts.append(f"[{note_type} — {date} — {author}]\n{content_text}")

    clinical_notes_text = "\n\n---\n\n".join(notes_parts) or "(No clinical notes available)"

    # ── Step 3: Package HCC V28 reference for agent ──────────────────────────
    # Include the full map so Po's agent can map any clinical finding to a code
    hcc_reference_v28 = {
        code: {
            "hcc":   entry["hcc"],
            "label": entry["label"],
            "raf":   entry["raf"],
        }
        for code, entry in HCC_MAP.items()
        if entry["hcc"] > 0  # exclude non-HCC codes
    }

    # ── Step 4: Build patient identity ───────────────────────────────────────
    patient_id   = patient.get("id", "unknown")
    patient_name = "Unknown"
    if patient.get("name") and len(patient["name"]) > 0:
        patient_name = patient["name"][0].get("text", "Unknown")

    # ── Step 5: Compose audit summary for agent ───────────────────────────────
    hcc_coded_count = sum(1 for c in coded_conditions_detail if c["hcc_code"] and c["hcc_code"] > 0)
    audit_summary = (
        f"Patient {patient_name} has {len(existing_codes)} coded condition(s), "
        f"of which {hcc_coded_count} map to HCC V28 codes. "
        f"Current RAF: {current_raf:.3f} (~${current_raf * 10_000:,.0f}/yr). "
        f"{len(notes_parts)} clinical note(s) available for CDI review. "
        f"Analyze clinical_notes_text for undocumented conditions and map to "
        f"hcc_reference_v28 codes to identify revenue gaps."
    )

    return {
        # Patient identity
        "patient_id":   patient_id,
        "patient_name": patient_name,

        # Current RAF (deterministic — no LLM)
        "current_raf":   current_raf,
        "projected_raf": current_raf,   # Po's agent updates this after gap analysis
        "raf_delta":     0.0,           # Po's agent updates this after gap analysis

        # Coded conditions (the problem list)
        "existing_codes":         existing_codes,
        "coded_conditions_detail": coded_conditions_detail,

        # Clinical notes — Po's agent performs CDI analysis on this text
        "clinical_notes_text": clinical_notes_text,
        "note_count":          len(notes_parts),

        # HCC V28 reference — Po's agent uses this to map findings to codes
        "hcc_reference_v28": hcc_reference_v28,

        # Gaps — empty from this function; Po's agent populates via analysis
        "gaps":      [],
        "gap_count": 0,

        # Audit summary
        "audit_summary": audit_summary,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5Ts Deliverable Formatter
# ─────────────────────────────────────────────────────────────────────────────

# Industry standard: $10,000 per RAF point for Medicare Advantage plans
_REVENUE_PER_RAF_POINT: float = 10_000.0


def format_5ts(audit: dict) -> dict:
    """
    Scaffold the 5Ts deliverable framework from audit_hcc_gaps() output.

    When called immediately after audit_hcc_gaps() (before Po's agent analysis),
    gaps will be empty and the Table/Template/Task are pre-formatted with the
    current RAF baseline. Po's agent fills in the gap analysis.

    When called with a gap-enriched audit dict (Po's agent has added gaps),
    produces the complete 5Ts report.

    Returns:
        {
          "table":    str  — RAF Baseline Scorecard (+ gap rows if gaps present)
          "template": str  — Physician query scaffold
          "task":     dict — RCM workflow ticket JSON
          "talk":     str  — Plain-English summary for the CDI specialist
        }
    """
    patient_name  = audit.get("patient_name", "Unknown Patient")
    patient_id    = audit.get("patient_id", "?")
    current_raf   = audit.get("current_raf", 0.0)
    projected_raf = audit.get("projected_raf", current_raf)
    raf_delta     = audit.get("raf_delta", 0.0)
    gaps          = audit.get("gaps", [])

    current_rev   = round(current_raf  * _REVENUE_PER_RAF_POINT, 2)
    projected_rev = round(projected_raf * _REVENUE_PER_RAF_POINT, 2)
    revenue_delta = round(raf_delta    * _REVENUE_PER_RAF_POINT, 2)

    # ── TABLE ─────────────────────────────────────────────────────────────────
    gap_rows = []
    for g in sorted(gaps, key=lambda x: x.get("raf_delta", 0.0), reverse=True):
        gap_rev = round(g.get("raf_delta", 0.0) * _REVENUE_PER_RAF_POINT, 2)
        gap_rows.append(
            f"| {patient_name} | {g.get('suspected_icd10','?')} "
            f"| {g.get('description','?')[:45]} "
            f"| HCC {g.get('suspected_hcc','?')} "
            f"| {g.get('confidence','?')} "
            f"| +{g.get('raf_delta',0.0):.3f} "
            f"| **+${gap_rev:,.0f}** |"
        )

    table = (
        "## 📊 RAF Gap Scorecard (Table)\n\n"
        f"**Patient:** {patient_name} | **ID:** `{patient_id}`\n"
        f"**Current RAF:** {current_raf:.3f} (≈ ${current_rev:,.0f}/yr)"
    )
    if gaps:
        table += (
            f" → **Projected RAF:** {projected_raf:.3f} (≈ ${projected_rev:,.0f}/yr)\n"
            f"**Net Revenue Recovery:** **+${revenue_delta:,.0f}**\n\n"
            "| Patient | ICD-10 | Condition | HCC | Confidence | RAF Delta | Est. Revenue Impact |\n"
            "|---------|--------|-----------|-----|------------|-----------|---------------------|\n"
        ) + "\n".join(gap_rows)
    else:
        table += (
            "\n**Gaps:** Pending CDI analysis by agent — review `clinical_notes_text`.\n"
        )

    # ── TEMPLATE ──────────────────────────────────────────────────────────────
    if gaps:
        top_gap   = gaps[0]
        evidence  = top_gap.get("evidence_quote", "documented in clinical notes")
        rationale = top_gap.get("clinical_rationale", "")
        icd10     = top_gap.get("suspected_icd10", "?")
        desc      = top_gap.get("description", "?")
        template  = (
            "## 📄 Physician Query (Template)\n\n"
            f"**RE: Clinical Documentation Improvement — {patient_name}**\n\n"
            "Dear Attending Physician,\n\n"
            f"During a routine CDI audit for **{patient_name}** (ID: `{patient_id}`), "
            f"our team identified a potential documentation gap. Specifically:\n\n"
            f"  - **Documented evidence:** \"{evidence[:200]}\"\n"
            f"  - **Suggested code:** `{icd10}` — {desc}\n"
            f"  - **Clinical rationale:** {rationale}\n\n"
            "Under CMS HCC Model V28, this condition must be explicitly coded each plan year "
            "to preserve Medicare Advantage reimbursement. If you agree that this condition "
            "is clinically present and actively managed, please amend the problem list "
            f"to include **{icd10}** at your earliest convenience.\n\n"
            "If you do not agree, no action is needed — please document your reasoning "
            "in the chart.\n\n"
            "Thank you for your continued partnership in clinical documentation excellence.\n\n"
            "*HCC Risk Navigator | Revenue Integrity Team*"
        )
    else:
        template = (
            "## 📄 Physician Query (Template)\n\n"
            f"**RE: Pending CDI Review — {patient_name}**\n\n"
            "Agent CDI analysis in progress. Query will be generated once coding gaps "
            "are identified from the clinical notes."
        )

    # ── TASK ──────────────────────────────────────────────────────────────────
    import datetime as _dt
    task = {
        "type":      "Task",
        "title":     f"V28 HCC Gap Review — {patient_name}",
        "patient_id":   patient_id,
        "patient_name": patient_name,
        "priority":     "HIGH" if revenue_delta > 2000 else "MEDIUM" if gaps else "LOW",
        "estimated_revenue_recovery": f"${revenue_delta:,.0f}" if gaps else "Pending analysis",
        "current_raf":  current_raf,
        "projected_raf": projected_raf,
        "gap_count":    len(gaps),
        "gaps_summary": [
            {
                "icd10":          g.get("suspected_icd10"),
                "description":    g.get("description"),
                "confidence":     g.get("confidence"),
                "revenue_impact": f"${round(g.get('raf_delta', 0) * _REVENUE_PER_RAF_POINT):,.0f}",
            }
            for g in gaps
        ],
        "action_required": (
            "Physician query sent. Await chart amendment or denial within 14 days."
            if gaps else "Pending agent CDI analysis of clinical notes."
        ),
        "assignee": "RCM Revenue Integrity Team",
        "due_date": (_dt.date.today() + _dt.timedelta(days=14)).isoformat(),
        "status":   "OPEN",
    }

    # ── TALK ──────────────────────────────────────────────────────────────────
    talk = (
        f"## 💬 Audit Summary (Talk)\n\n"
        f"{audit.get('audit_summary', 'No summary available.')}\n\n"
    )
    if gaps:
        talk += (
            f"**Bottom line:** {len(gaps)} HCC coding gap(s) identified for **{patient_name}**. "
            f"Capturing these gaps could recover approximately **${revenue_delta:,.0f}** in annual "
            f"Medicare Advantage revenue (RAF: {current_raf:.3f} → {projected_raf:.3f})."
        )
    else:
        talk += (
            f"**Next step:** Review `clinical_notes_text` against `hcc_reference_v28` to identify "
            f"any conditions documented in the notes but absent from the {len(audit.get('existing_codes', []))} "
            f"coded condition(s) on the current problem list."
        )

    return {
        "table":    table,
        "template": template,
        "task":     task,
        "talk":     talk,
    }
