# FIRE: FHIR-Integrated Revenue Engine
*(Prompt Opinion "Agents Assemble" Hackathon Submission)*

## Executive Summary
FIRE is a deterministic, multi-agent AI pipeline that directly interfaces with FHIR R4 servers to automatically audit patient records for CMS V28 HCC coding gaps. By combining a structural MCP tool for data retrieval with three specialized AI agents, FIRE identifies undocumented clinical conditions, gets them verified against CMS MEAT standards, and calculates exact revenue recovery metrics.

**Business Model:** FIRE operates on a shared savings model. We charge minimal upfront SaaS fees, taking exactly 10% of the net new RAF revenue generated from our identified and approved coding gaps. This perfectly aligns our incentives with the hospital's financial outcomes.

## The Technology Stack
* **FastAPI + FastMCP**: Serves the `audit_v28_cohort` MCP tool.
* **SHARP Protocol Middleware & HTI-1 Interoperability**: Intercepts `X-FHIR-Server-URL` and authentication headers. By using the SHARP extension specs and FHIR standards, FIRE is fully compatible with **Darena Health** and HTI-1 mandates, making it capable of plugging instantly into any compliant EHR connected to the platform.
* **Live FHIR R4 Integration**: We do not use fake mock data for the demo. FIRE queries a live, public HAPI FHIR server. You can view one of our exact hydrated patients (Tamara Williams) live on the network here:
  * [View FHIR Patient Resource](https://hapi.fhir.org/baseR4/Patient/132026010)
  * [View FHIR Clinical Note (Base64 Encoded DocumentReference)](https://hapi.fhir.org/baseR4/DocumentReference?subject=Patient/132026010)

![Architecture Diagram](./assets/architecture.png)

## The Multi-Agent Topology
FIRE leverages the "Agents Assemble" framework by orchestrating three distinct personas in a strict data-handoff topology:

1. **Clinical Orchestrator (Manager)**: Runs the MCP tool `audit_v28_cohort` to fetch FHIR data. Crucially, it acts as a pure data pipeline, serializing the raw JSON array and handing it directly to the analyst agent to prevent LLM context fragmentation.
2. **HCC Risk Navigator (Analyst)**: A sub-agent dedicated exclusively to cross-referencing `clinical_notes_text` against the CMS V28 HCC dictionary. It identifies the gaps and calculates the RAF math (Current vs. Projected). It has native vectorstore access to the official ICD-10 MS-DRG Version 43.1 guidelines to pull precise diagnostic codes without hallucinating.
3. **Compliance Reviewer (The Zero-Trust Firewall)**: A final checkpoint agent that acts as a zero-trust gatekeeper. It does not have direct database or FHIR access. Its sole purpose is to prevent fraud by verifying that all proposed codes are backed by strict CMS M.E.A.T. (Monitor, Evaluate, Assess, Treat) criteria found in the clinical notes. It is grounded via a native PubMed integration, allowing it to cross-reference prescribed treatments against established medical literature to validate the clinical care.

![Multi-Agent Hand-off](./assets/agent_topology.png)

## The Demo Execution (Step-by-Step)
To guarantee flawless, deterministic execution without LLM context overload, the demonstration is run through a strict 3-step manual hand-off using the direct agent chat interface. The judges can easily reproduce this exact output.

### Step 1: Cohort Triage & Baseline Scorecard
To prioritize the clinical documentation workflow, the engine first establishes a financial baseline. It calculates the current value of each patient's coded conditions and scans the FHIR records to triage the queue, flagging exactly who has unreviewed unstructured clinical notes hiding potential lost revenue.

**Prompt:**
```text
Run a baseline audit on our newest FHIR patient cohort and show me the scorecard. I need to see the current RAF value of the group and identify exactly which patients have clinical notes attached that are ready for gap analysis.
```
**Output Highlights:**
![Step 1 Scorecard](./assets/step1_scorecard.png)
*(Shows 6 patients fetched from FHIR, highlighting Tamara, Richard, and Maria as having pending gap analysis due to attached clinical notes).*

### Step 2: Deterministic Risk Analysis
*(Switch your chat to the **HCC Risk Navigator** agent)*
**Prompt:**
```text
Analyze this FHIR JSON for Tamara Williams, Richard Chen, and Maria Gonzalez against the V28 guidelines using your ICD-10 MS-DRG vectorstore. I need to see the exact gap descriptions, the vectorstore citations proving the codes, and the projected revenue impact. 

[PASTE THE JSON FROM STEP 1 HERE]
```
**Output Highlights:**
![Step 2 Gap Findings](./assets/step2_gaps.png)
*(Successfully identifies E11.40 for Tamara, J44.1 for Richard, and N18.4 for Maria with exact RAF Deltas).*

### Step 3: Compliance Verification & The 5Ts Deliverable
*(Switch your chat to the **Compliance Reviewer** agent)*
**Prompt:**
```text
Verify these clinical gaps against CMS M.E.A.T. standards. Use your PubMed access to ensure the prescribed treatments legitimately match the proposed diagnosis. 

Then, compile the findings into a complete 5Ts deliverable. Explicitly calculate the total projected RAF delta and the final revenue impact at $10,000 per 1.0 RAF. List out the verified physician queries. Address the queries to "Dr. Sarah Jenkins, MD" and ensure you cite the exact FHIR DocumentReference IDs.

[PASTE THE GAP OUTPUT FROM STEP 2 HERE]
```
**Output Highlights:**
![Step 4 Final Output](./assets/step4_5ts.png)
*(Final report yields $9,540 in immediate revenue impact, fully customized Physician Query letters, and zero LLM hallucinations).*

## Market Analysis & Revenue Projections
To understand the financial scale of this technology, here is a highly conservative market analysis for deploying FIRE at a typical mid-sized regional hospital:

**Conservative Assumptions:**
* **Medicare Advantage Panel**: 10,000 patients.
* **Gap Prevalence**: Only 5% of patients (500) have an undocumented HCC gap buried in their unstructured clinical notes.
* **Average Gap Value**: A minor +0.200 RAF increase per gap (approx. $2,000/yr per patient).

**Hospital Financial Impact:**
* 500 patients × $2,000 = **$1,000,000 in recovered annual revenue**.
* Cost to hospital: $0 upfront. No new clinical documentation integrity (CDI) headcount required.

**FIRE Business Model (10% Shared Savings):**
* $1,000,000 × 10% = **$100,000 Annual Recurring Revenue (ARR)** for FIRE per hospital.
* Capturing just 10 mid-sized hospitals yields a $1M ARR SaaS business with near-zero marginal cost, as the deterministic multi-agent pipeline operates entirely autonomously.

## Glossary of Terms
To help judges unfamiliar with healthcare Revenue Cycle Management (RCM) understand the exact value of this pipeline, here are the key terms used:

* **FIRE**: FHIR-Integrated Revenue Engine. The name of our project and MCP backend server.
* **FHIR (Fast Healthcare Interoperability Resources)**: The modern, global API standard for exchanging electronic health records (EHR).
* **ICD-10 Codes**: The universal alphanumeric codes used by clinicians to classify every disease, injury, and symptom.
* **HCC (Hierarchical Condition Category)**: A risk-adjustment model used by Medicare. Not all ICD-10 codes map to an HCC. HCC codes carry a specific "weight" that translates directly to higher Medicare reimbursement for treating sicker patients.
* **RAF (Risk Adjustment Factor)**: A patient's cumulative health score, calculated by adding up the weights of all their active HCC codes. A higher RAF score means the hospital gets paid more annually to manage that patient's complex care. ($10,000 per 1.0 RAF).
* **CMS V28**: The newest, much stricter version of the Medicare HCC scoring model. In V28, generic diagnoses are now worth $0. Hospitals are currently losing millions of dollars in revenue because their documentation isn't specific enough to meet V28's requirements.
* **CMS MEAT Standards**: To legally claim an HCC code, a doctor's clinical note must explicitly show they are **M**onitoring, **E**valuating, **A**ssessing, or **T**reating the condition. Our Compliance Reviewer agent specifically verifies this to prevent fraud.
