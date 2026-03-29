# 🎬 3-Minute Demo Script — Clinical Orchestrator

**0:00 - 0:45 | The Problem & The UI**

**Screen**: Start with your Streamlit UI taking up the full screen. Show Tamara's chart. Highlight the current RAF score, then highlight the clinical notes mentioning "burning feet" and "Gabapentin."

**Audio/Script**: "Hospitals lose millions of dollars annually because physicians document clinical conditions in their notes but fail to capture the corresponding ICD-10 billing codes. In this mock EHR, we can see Tamara has a low RAF score, but her unstructured notes clearly indicate diabetic neuropathy. To capture this revenue securely, we built a multi-agent swarm."

---

**0:45 - 1:30 | The Architecture & Execution**

**Screen**: Switch to the Prompt Opinion platform. Show the Launchpad with the Orchestrator selected. Ensure the "Show Tool calls" UI element is visible.

**Action**: Type the prompt: *"I am prepping the chart for her annual wellness visit today. Please run an audit for missing revenue opportunities."* Hit Enter.

**Audio/Script**: "Instead of a basic chat bot, we are utilizing the platform's native Orchestrator agent to execute a zero-touch workflow. When I request an audit, the Orchestrator securely passes the patient's FHIR context using SHARP specs to our first sub-agent: the HCC Risk Navigator. Because we require patient data access, the agent reaches through an MCP tunnel to our local Python backend, queries the mock database, and calculates the exact financial impact."

---

**1:30 - 2:15 | The A2A Handoff & Compliance Check**

**Screen**: Let the video capture the UI as it shows the A2A handoff from the HCC agent to the Compliance agent (no clicking required, just let the native orchestrator work).

**Audio/Script**: "This is where the Agent-to-Agent, or A2A, handoff happens. Clinical coding cannot happen in a vacuum. The Orchestrator takes the financial findings and routes them directly to our Compliance Reviewer agent. This agent evaluates the extracted clinical evidence strictly against CMS MEAT documentation standards."

---

**2:15 - 3:00 | The Payoff (The Last Mile)**

**Screen**: Scroll through the final, perfectly formatted Markdown report. Highlight the financial impact and the drafted physician query at the bottom.

**Audio/Script**: "In seconds, the swarm completes the audit. It identified code E11.40, calculated a $3,624 revenue opportunity, and secured compliance approval. To solve the 'Last Mile' of healthcare AI, the system automatically drafts the exact query needed for the attending physician to officially append the code to the chart. This is deterministic, secure, and interoperable clinical automation. Thank you."
