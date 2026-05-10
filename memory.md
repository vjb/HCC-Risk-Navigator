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

## Root Cause Hypothesis
The **Primary Clinical Orchestrator** is failing to pass the full FHIR context (specifically the `clinical_notes_text` and problem lists) to the **HCC Risk Navigator** sub-agent for all three patients simultaneously. The orchestrator may be truncating the payload, dropping context, or the Risk Navigator is incorrectly attempting to query the FHIR database directly instead of relying purely on the text handed off by the Orchestrator.

## Next Steps upon Session Restart
1.  **Investigate Context Handoff**: Review the Prompt Opinion chat logs or execution traces to see exactly what the Orchestrator sent to the Risk Navigator in Step 2.
2.  **Prompt Adjustment**: We may need to explicitly instruct the Orchestrator (in `docs/prompts.md`) to serialize and send the COMPLETE clinical notes array for ALL flagged patients when invoking the Risk Navigator tool.
3.  **MCP Tool Check**: Verify if `hcc_engine.py` is correctly packaging the notes for all 3 patients in the Step 1 output so the Orchestrator has them in memory to pass along.
4.  **Resume Recording**: Once the handoff is fixed and all 3 patients are successfully audited in Step 2, resume the browser auto-recording sequence.
