# FIRE Project Memory & State

## Current Repository State
*   **Documentation Hardening Complete**: The repository has been fully updated to comply with the "Anti-BS Institutional Protocol." All marketing fluff, em-dashes, and legacy terminology (e.g., "Master", "Zero-Trust Firewall") have been purged.
*   **Demo Script Finalized**: The `README.md` and `docs/demo_script.md` reflect a highly conversational, 5-step flow.
*   **Prompt Architecture Fixed**: I have proactively updated the system prompts in `docs/prompts.md` to strictly enforce the "100% Real FHIR" data handoff protocol, removing improper tool usage from sub-agents.

## Confirmed Issue (Live Demo Failures)
During the latest attempts to run the demo on the Prompt Opinion platform, the conversational flow failed at **Step 2 (Risk Navigator)** and **Step 4 (Compliance Reviewer)**.
*   **Risk Navigator Failure**: Failed to analyze Tamara and Maria because it attempted to invoke its own MCP tool to refetch the data from the unstable HAPI FHIR server, rather than relying on the Orchestrator's context.
*   **Compliance Reviewer Failure**: Rejected all 3 patients, explicitly stating "Lack of clinical documentation" and "Absence of clinical notes."

## Root Cause & The Fix
The **Primary Clinical Orchestrator** was failing to pass the full FHIR context (specifically the `clinical_notes_text` array) into its messages to the sub-agents. Because the sub-agents were starved of context, they either hallucinated tool calls to refetch the data (Risk Navigator) or outright rejected the workflow (Compliance Reviewer).

**Proactive Fixes Applied:**
1.  **Orchestrator Prompt**: I updated `docs/prompts.md` to strictly command the Orchestrator to *extract* the `clinical_notes_text` for ALL flagged patients from the `patient_audits` array and paste the FULL text verbatim into its handoff messages.
2.  **Risk Navigator Prompt**: I stripped the `audit_hcc_opportunities` tool from the Risk Navigator's instructions and explicitly commanded it to "DO NOT attempt to call external tools to fetch patient data." It must now rely solely on the notes provided in the message.

## Next Steps upon Session Restart
1.  **Platform Update**: Copy the newly updated prompts from `docs/prompts.md` and paste them into the Prompt Opinion platform to update the agent configurations.
2.  **Resume Recording**: Once the agents are updated on the platform, execute the 5-step conversational demo again. The Orchestrator will now correctly pass the raw FHIR text, and the sub-agents will process the data without failing.
