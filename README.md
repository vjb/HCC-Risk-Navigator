# FIRE: FHIR-Integrated Revenue Engine

## Architecture Overview
FIRE is a multi-agent system that interfaces with FHIR R4 servers to audit patient records for CMS V28 HCC coding gaps. The system utilizes an MCP tool for data retrieval and three agents to identify clinical conditions, verify them against CMS M.E.A.T. standards, and calculate revenue metrics.

## Business Case
FIRE operates on a shared savings model. The system requires minimal upfront SaaS fees, taking exactly 10% of the net new RAF revenue generated from identified and approved coding gaps. This aligns platform incentives with the hospital's financial outcomes.

## System Integrations
The FIRE MCP Server and Agents are deployed on the Prompt Opinion platform:
* [FIRE MCP Tool](https://app.promptopinion.ai/marketplace/mcp/019d39ef-c21c-703d-a526-e8bcaf8b4fb8)
* [HCC Risk Navigator Agent](https://app.promptopinion.ai/marketplace/agent/019d39f2-f707-719a-b3f1-396b997b5f47)
* [Compliance Reviewer Agent](https://app.promptopinion.ai/marketplace/agent/019d39f3-f6da-779b-b85a-ec474cfde56a)

## Technology Stack
* **FHIR R4 Integration**: FIRE queries a public HAPI FHIR server. A test patient record is available here:
  * [View FHIR Patient Resource](https://hapi.fhir.org/baseR4/Patient/132026010)
  * [View FHIR Clinical Note (Base64 Encoded DocumentReference)](https://hapi.fhir.org/baseR4/DocumentReference?subject=Patient/132026010)
* **Cloud Deployment**: The MCP backend is deployed as a service on Render. The active endpoints are:
  * [Live MCP Server SSE Endpoint](https://fire-mcp-backend.onrender.com/mcp/sse)
  * [Interactive Swagger UI (/docs)](https://fire-mcp-backend.onrender.com/docs)
  * [OpenAPI Schema (/openapi.json)](https://fire-mcp-backend.onrender.com/openapi.json)
* **FastAPI and FastMCP**: Serves the `audit_v28_cohort` MCP tool.
* **SHARP Protocol Middleware and HTI-1 Interoperability**: Intercepts `X-FHIR-Server-URL` and authentication headers. FIRE adheres to the SHARP extension specifications and FHIR standards for EHR interoperability.

## Agent Topology
FIRE orchestrates three distinct agents in a sequential data-handoff topology:

1. **Clinical Orchestrator**: Executes the MCP tool `audit_v28_cohort` to fetch FHIR data. It functions as a data pipeline, managing the initial handoff to sub-agents and routing the final JSON payload to the enterprise RCM system (e.g., Jira, Epic).
2. **HCC Risk Navigator**: A sub-agent that cross-references `clinical_notes_text` against the CMS V28 HCC dictionary. It identifies documentation gaps and calculates the RAF delta. It queries a vectorstore containing the ICD-10 MS-DRG Version 43.1 guidelines to retrieve diagnostic codes.
3. **Compliance Reviewer**: A validation agent that acts as a compliance gatekeeper. It does not have direct database or FHIR access. It verifies that proposed codes meet CMS M.E.A.T. (Monitor, Evaluate, Assess, Treat) criteria based on the clinical notes. It utilizes a PubMed integration to cross-reference prescribed treatments against medical literature.

```mermaid
sequenceDiagram
    participant Orch as Clinical Orchestrator
    participant RN as Risk Navigator
    participant CR as Compliance Reviewer
    participant RCM as Enterprise RCM Engine
    
    Orch->>RN: 1. Send FHIR Clinical Notes
    RN-->>Orch: 2. Return Identified Gaps and RAF Delta
    
    Orch->>CR: 3. Send Gaps for M.E.A.T. Verification
    CR-->>Orch: 4. Return Verified JSON Deliverable
    
    Orch->>RCM: 5. Route Task JSON Payload
```

### Agent Configurations
The agent system prompts for the Orchestrator, Risk Navigator, and Compliance Reviewer are documented here:
[View Agent System Prompts (`docs/prompts.md`)](docs/prompts.md)

## Execution Pipeline
Note: This pipeline can be automated to schedule tasks in an enterprise workflow system. For demonstration purposes, it is executed sequentially to verify outputs.

### Step 1: Cohort Triage and Baseline Scorecard
The system calculates the current value of each patient's coded conditions and scans the FHIR records to identify patients with unreviewed clinical notes.

**Prompt:**
```text
Run a baseline audit on our newest FHIR patient cohort and show me the scorecard.
```

![Baseline Scorecard](assets/step1_baseline.png)

### Step 2: Risk Analysis
The Risk Navigator agent cross-references the retrieved clinical text against the CMS V28 dictionary to identify hidden coding gaps.

**Prompt:**
```text
Run the HCC gap analysis audit on all patients marked ready for audit and list them.
```

![Gap Analysis Results](assets/step2_gap_analysis.png)

### Step 3: RAF Impact Calculation
The system calculates the exact cumulative Risk Adjustment Factor (RAF) delta across the cohort and projects the corresponding financial impact.

**Prompt:**
```text
so whats the total raf increase and revenue impact potential?
```

![RAF Impact Calculation](assets/step3_raf_impact.png)

### Step 4: Compliance Verification
The Compliance Reviewer verifies the proposed diagnostic codes against CMS M.E.A.T. criteria using a native PubMed integration to validate treatment protocols.

**Prompt:**
```text
check with compliance
```

![Compliance Verification](assets/step4_compliance.png)

### Step 5: System Integration and Workflow Hand-Off
The Orchestrator generates a structured JSON payload containing the verified clinical data and compliance decisions for routing into the hospital's RCM engine.

**Prompt:**
```text
write the json to generate the task in epic in hcls format assign dates two days from now and assign to dr. smith
```

**JSON Output Payload:**
```json
[
  {
    "type": "Task",
    "title": "Add Diabetic Peripheral Neuropathy Code",
    "patientId": "132026010",
    "assignee": "Dr. Smith",
    "dueDate": "2023-11-05",
    "priority": "High",
    "details": {
      "clinicalEvidence": "Patient presents for routine follow up of type 2 diabetes. Assessment: Diabetic peripheral neuropathy.",
      "currentCode": "E11.9",
      "suggestedCode": "E11.40",
      "rafDelta": 0.198,
      "revenueImpact": "$1,980",
      "actionRequired": "Confirm the addition of ICD-10 code E11.40 for Diabetic Peripheral Neuropathy."
    }
  },
  {
    "type": "Task",
    "title": "Add COPD with Exacerbation Code",
    "patientId": "132026013",
    "assignee": "Dr. Smith",
    "dueDate": "2023-11-05",
    "priority": "High",
    "details": {
      "clinicalEvidence": "Assessment: Acute exacerbation of COPD.",
      "currentCode": null,
      "suggestedCode": "J44.1",
      "rafDelta": 0.335,
      "revenueImpact": "$3,350",
      "actionRequired": "Ensure ICD-10 code J44.1 is included on the active problem list."
    }
  },
  {
    "type": "Task",
    "title": "Add Stage 4 CKD Code",
    "patientId": "132026016",
    "assignee": "Dr. Smith",
    "dueDate": "2023-11-05",
    "priority": "High",
    "details": {
      "clinicalEvidence": "Assessment: Stage 4 chronic kidney disease. eGFR of 22 mL/min/1.73m2.",
      "currentCode": null,
      "suggestedCode": "N18.4",
      "rafDelta": 0.421,
      "revenueImpact": "$4,210",
      "actionRequired": "Confirm the inclusion of ICD-10 code N18.4 based on documented eGFR levels."
    }
  }
]
```



## Core Implementation Files

| File | Core Purpose | Prompt Opinion Integration Proof |
|------|--------------|--------------------------------|
| [`src/server.py`](src/server.py) | FastMCP Server and Auth | **[Capability Injection (L413-L431)](src/server.py#L413-L431):** Extends the FastMCP initialization options to register the `ai.promptopinion/fhir-context` capability. This authenticates and processes Prompt Opinion's SHARP headers and dynamic FHIR context. |
| [`src/hcc_engine.py`](src/hcc_engine.py) | Baseline Calculator | **[Raw Context Handoff (L180-L208)](src/hcc_engine.py#L180-L208):** Calculates the baseline mathematically using CMS V28 maps, and packages the raw `clinical_notes_text` array for the Prompt Opinion LLM agent. |

## Glossary of Terms
Please refer to the [Glossary of Terms](docs/glossary.md) for definitions of acronyms and regulatory terminology used in this repository.

## Phase 2
* **Event-Driven Architecture**: Subscribing to live `DocumentReference` creation events via webhooks for automated execution.
* **Scope of Analysis**: Incorporating standard CPT codes for E&M Leveling and SDOH Z-codes.
* **EHR Write-Back**: Implementing a direct closed-loop SMART on FHIR POST request to the clinician's inbox.
