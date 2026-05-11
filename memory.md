# FIRE Project Memory & State

## Current Repository State
*   **Documentation Hardening Complete**: The repository has been fully updated to comply with the "Anti-BS Institutional Protocol." All marketing fluff, em-dashes, and legacy terminology (e.g., "Master", "Zero-Trust Firewall") have been purged.
*   **Demo Script Finalized**: The `README.md` and `docs/demo_script.md` reflect a highly conversational, 5-step flow.
*   **Prompt Architecture Fixed**: I have proactively updated the system prompts in `docs/prompts.md` to strictly enforce the "100% Real FHIR" data handoff protocol, removing improper tool usage from sub-agents.

## Confirmed Issue (Live Demo Failures)
During the latest attempts to run the demo on the Prompt Opinion platform, the conversational flow failed at **Step 2 (Risk Navigator)** and **Step 4 (Compliance Reviewer)**.
*   **Risk Navigator Failure**: Failed to analyze Tamara and Maria because it attempted to invoke its own MCP tool to refetch the data from the unstable HAPI FHIR server, rather than relying on the Orchestrator's context.
*   **Compliance Reviewer Failure**: Rejected all 3 patients, explicitly stating "Lack of clinical documentation" and "Absence of clinical notes."

## Root Cause & The Fix (Compliance Handoff Failure)
The **Primary Clinical Orchestrator** failed the compliance check step because it passed the exact gaps and calculated RAF/revenue data, but it FAILED to pass the `clinical_notes_text` to the Compliance Reviewer. Because the Reviewer lacked the clinical notes, it rejected all patients stating it could not assess M.E.A.T. criteria.

**Proactive Fixes Applied:**
1.  **Orchestrator Prompt**: I updated `docs/prompts.md` to strictly command the Orchestrator to *pass the exact gaps, calculated RAF/revenue data, AND the full `clinical_notes_text`* to the Compliance Reviewer.
2.  **Risk Navigator Math Fix**: I updated the Risk Navigator prompt to explicitly calculate the exact `raf_delta` using the `hcc_reference_v28` table and multiply it by $10,000 for the Revenue Impact.

## Next Steps upon Session Restart
1.  **Platform Update**: Update the "Primary Clinical Orchestrator" agent on the Prompt Opinion platform with the newly updated system prompt.
2.  **Record E2E Demo**: Execute the 5-step conversational demo end-to-end to verify the Orchestrator successfully passes the clinical notes to the Compliance Reviewer, and the JSON payload is accurately generated.
