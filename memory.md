# FIRE Project Memory & State

## Current Repository State
*   **Documentation Hardening Complete**: The repository has been fully updated to comply with the "Anti-BS Institutional Protocol." All marketing fluff, em-dashes, and legacy terminology (e.g., "Master", "Zero-Trust Firewall") have been purged.
*   **Demo Script Finalized**: The `README.md` and `docs/demo_script.md` now reflect a highly conversational, 5-step flow:
    1. Baseline audit & triage.
    2. Gap analysis for all flagged patients.
    3. RAF impact calculation.
    4. Compliance verification via PubMed.
    5. EPIC HCLS JSON task generation.
*   **Prompt Cleanups**: Removed the problematic requirement for explicit vectorstore page chunk citations in the HCC Risk Navigator prompt, which was causing hallucination/failure.

## Current Issue (Demo Recording Blocked)
During the latest attempt to record the 5-step demo on the Prompt Opinion platform, the conversational flow failed at **Step 2 (Gap Analysis)**.
*   **Step 1** succeeded in identifying the 3 patients ready for audit (Tamara, Richard, Maria).
*   **Step 2** partially succeeded for Richard Chen but **failed for Tamara Williams and Maria Gonzalez**.
*   **Error Observed**: The HCC Risk Navigator reported:
    *   *Tamara*: "Unable to retrieve full patient chart data; unable to calculate RAF or identify specific coding gaps directly from the available information."
    *   *Maria*: "Patient not found in the FHIR server or mock EHR system."

## Root Cause Hypothesis & Deep Dive
1. **Tool Refetching Failure**: In Step 2, the Risk Navigator is ignoring the Orchestrator's context and attempting to fetch the patient charts individually using its own `audit_hcc_opportunities` MCP tool.
2. **Missing Local Data**: The public HAPI FHIR server is unreliable. When the `audit_hcc_opportunities` tool fails to find the patients on HAPI, it falls back to the local SQLite DB (`data/mock_ehr.sqlite`).
3. **Seeding Limitation**: `scripts/seed_db.py` *only* seeds Tamara Williams. It does not seed Richard Chen or Maria Gonzalez. Therefore, the tool returns `{"error": "Patient ... not found in FHIR server or mock EHR."}` for Maria, which the LLM repeats verbatim in the output you saw.

## Next Steps upon Session Restart
1.  **Prompt Adjustment (Orchestrator)**: Update `docs/prompts.md` so the Orchestrator is forced to extract `clinical_notes_text` from the `patient_audits` array and pass it verbatim in its message to the Risk Navigator.
2.  **Prompt Adjustment (Risk Navigator)**: Instruct the Risk Navigator to *rely strictly on the clinical notes provided in the message* rather than calling the `audit_hcc_opportunities` tool to refetch data.
3.  **Alternative (DB Seeding)**: Alternatively, we could update `scripts/seed_db.py` to correctly seed Richard and Maria into the local Mock EHR so the tool fallback actually works.
4.  **Resume Recording**: Once these prompts/DB are fixed, run the demo sequence again.
