# FIRE Project - Session Checkpoint Memory

## Current State & Goals
- **Objective:** Finalize the end-to-end multi-agent Prompt Opinion demo for the FIRE hackathon, run it locally with ngrok, verify the outputs, and eventually deploy to Render for the Marketplace.
- **Project Structure:** 
  - `src/server.py`: FastMCP server exposing `audit_hcc_opportunities` and `audit_v28_cohort`.
  - `src/hcc_engine.py`: Pure deterministic FHIR logic and CMS V28 RAF calculator (no LLM, all intelligence happens in the Prompt Opinion agent via RAG).
  - `scripts/record_demo.py`: Playwright script to record the UI (updated to handle login synchronization).

## Last Known Status
1. **Local Server:** The `FastMCP` local backend (`server.py`) is successfully running on port `8000`.
2. **Ngrok:** User has successfully started ngrok. The active tunnel is `https://rafaela-inapproachable-kellie.ngrok-free.dev`.
3. **Current Action:** Awaiting user to update the Prompt Opinion UI with the new endpoint URL before running the demo prompts.

## Next Steps
1. ~~User starts `ngrok` manually in their terminal to ensure a stable tunnel.~~ (Done)
2. ~~User provides the new ngrok URL so the Prompt Opinion MCP configuration can be updated.~~ (Done)
3. ~~Run Prompt 1 to verify the Orchestrator works.~~ (Done! Scorecard generated successfully).
4. ~~Run Prompt 2 to verify the Risk Navigator gap analysis.~~ (Done!)
5. ~~Run Prompt 3 to verify the Compliance Reviewer and generate the 5Ts deliverable.~~ (Done!)
6. ~~Finalize the Render deployment strategy (`PORT` binding, `requirements.txt`, `render.yaml`) to eliminate ngrok entirely for the final hackathon submission.~~ (Done! Render files generated.)
