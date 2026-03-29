# 🎬 3-Minute Demo Script — HCC Risk Navigator

**Event:** Agents Assemble — The Healthcare AI Endgame  
**Presenter:** vincent beltrani  
**Total Runtime:** 3:00 minutes

---

## [0:00–0:30] The Setup — Show the Mock EHR

**Action:** Switch to the Streamlit dashboard at `http://localhost:8501`

**Say:**
> "Meet Tamara Williams — a 47-year-old Type 2 diabetic. Her chart only has a basic ICD-10 code for generic Diabetes (E11.9). This carries a low Risk Adjustment Factor (RAF), meaning the hospital is losing Medicare Advantage funding for her actual acuity."

**Point to on screen:**
- Patient banner: "Tamara Williams"
- Coded conditions: E11.9
- RAF Score: 0.104
- The Clinical Notes tab

**Say:**
> "If we read her unstructured clinical notes, Dr. Morrison clearly documented *worsening numbness and a burning sensation in both feet*, and initiated Gabapentin. This is Diabetic Peripheral Neuropathy! It's buried in the text but missing from the structured data. Normally, clinical documentation improvement (CDI) teams spend hours auditing charts for this exact 'HCC Gap'. We're going to use generative AI to do it in 5 seconds."

---

## [0:30–1:30] The Superpower — MCP HCC Agent

**Action:** Switch to the Prompt Opinion web platform

**Say:**
> "I'm stepping into the shoes of a CDI specialist. I'll use the Prompt Opinion orchestrator to run the audit."

**Type in the chat:**
> *"I am prepping the chart for her annual wellness visit today. Please run an audit for missing revenue opportunities."*

**Press Enter. Say:**
> "The orchestrator is securely calling out to our local FHIR-native MCP server via an ngrok tunnel. Our server pulls Tamara's full chart, feeds the structured problem list and unstructured notes to GPT-4o-mini, and surfaces the missing revenue."

**Action:** Switch momentarily to the terminal to show the logs lighting up.

**Switch back to Prompt Opinion. Say:**
> "Look at the output. It successfully identified the missing ICD-10 code: E11.40. It accurately pulled the supporting evidence quote from the notes, and calculated an incredible projected RAF jump from 0.104 to 0.406! But it doesn't stop there. Notice that our MCP tool strategically packed the underlying 'CMS MEAT Criteria' (Condition, Symptoms, and Treatments) directly into the evidence string for compliance."

---

## [1:30–2:30] Agent-to-Agent Handoff — Compliance Clearance

**Say:**
> "In healthcare, finding a missing code isn't enough; it must be rigorously audited against CMS MEAT compliance standards before we append it to the patient's record. Let's do an Agent-to-Agent handoff to the strict Compliance Reviewer."

**Type in the chat:**
> *"Send a message to the Compliance Reviewer containing the financial report and evidence quote."*

**Press Enter. Say:**
> "The general orchestrator is now talking laterally to the specialized Compliance Reviewer agent. Because our HCC MCP Server natively fed those embedded MEAT criteria forward, the compliance agent gets exactly the structured symptoms and management plans it demands."

**The agent's response should say:**
> *🟢 COMPLIANCE APPROVED: Clinical evidence meets CMS MEAT (Monitor, Evaluate, Assess, Treat) documentation standards. Authorized to append.*

---

## [2:30–3:00] The Endgame 

**Say:**
> "That right there is the Last Mile of healthcare revenue cycle AI. We didn't just summarize a document. We used a custom FHIR-native Model Context Protocol server to find an uncoded condition, surfaced the exact missed revenue, and seamlessly orchestrated a compliant agent-to-agent peer review to guarantee Medicare Advantage payment integrity. 

> Thank you."
