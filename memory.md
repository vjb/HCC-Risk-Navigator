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
2. **HAPI FHIR Instability**: The public HAPI FHIR server is unreliable under repeated immediate queries. When the `audit_hcc_opportunities` tool fails to find the patients on HAPI during this redundant secondary fetch, it returns a "Patient not found" error, which the LLM repeats verbatim.

## Next Steps upon Session Restart
1.  **Prompt Adjustment (Orchestrator)**: Update `docs/prompts.md` so the Orchestrator is forced to extract `clinical_notes_text` from the `patient_audits` array and pass it verbatim in its message to the Risk Navigator.
2.  **Prompt Adjustment (Risk Navigator)**: Instruct the Risk Navigator to *rely strictly on the clinical notes provided in the message* rather than calling the `audit_hcc_opportunities` tool to refetch data.
3.  **Resume Recording**: Once the prompts are fixed to enforce strict data hand-offs without refetching, run the demo sequence again.
