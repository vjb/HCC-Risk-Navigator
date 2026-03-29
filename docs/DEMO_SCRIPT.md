# 🎬 3-Minute Demo Script — Auto-Auth Pre-Cog Engine

**Event:** Agents Assemble — The Healthcare AI Endgame
**Presenter:** [Your Name]
**Total Runtime:** 3:00 minutes

---

## [0:00–0:30] The Setup — Show the Mock EHR

**Action:** Switch to the Streamlit dashboard at `http://localhost:8501`

**Say:**
> "Meet Tamara Chen — a 47-year-old Type 2 diabetic. Her doctor wants to prescribe Ozempic, but Aetna's step therapy policy requires 6 months of Metformin first. Look at her record — she only completed 2 months."

**Point to on screen:**
- Patient banner: "Tamara Chen" with her demographics
- Step-therapy progress bar: **61 days / 180 days** (⚠️ red)
- A1C trend chart: Rising from 7.8% → 8.6% (not controlled)
- The ⚠️ PA Alert banner at the top

**Say:**
> "Normally this is an automatic denial. But there's a clinical note here..."

**Click:** Clinical Notes tab
> "Dr. Morrison documented *severe GI intolerance to Metformin* — nausea, cramping, diarrhea. She discontinued it. That's a qualifying clinical exception under Aetna's own policy. A human would spend hours finding this and writing the letter. We're going to do it in seconds."

---

## [0:30–1:30] The A2A Handoff — Prompt Opinion UI

**Action:** Switch to the Prompt Opinion web platform

**Say:**
> "Now I'm in the Prompt Opinion General Chat Agent. I'm going to trigger the Prior Auth workflow."

**Type in the chat:**
> *"I want to prescribe Ozempic for patient Tamara Chen (ID: tamara-chen-001). She failed Metformin step therapy due to GI intolerance. Please consult the Prior Auth Agent and generate a PA Exception Request."*

**Press Enter. Say:**
> "Watch what happens next. The General Chat Agent is now doing an Agent-to-Agent handoff to our specialized Prior Authorization agent, which is connected to our local MCP server via this ngrok tunnel."

**Point to:** The ngrok URL in the Prompt Opinion MCP server configuration

---

## [1:30–2:30] The Superpower in Action — MCP Tools Firing

**Action:** Switch to the terminal running the MCP server

**Say:**
> "Look at these logs lighting up in real time."

**Expected log output to appear:**
```
[INFO] 🔍 get_fhir_context called for patient_id='tamara-chen-001'
[INFO] ✅ Returning FHIR context: 1 meds, 3 obs, 1 notes
[INFO] 🩺 hunt_clinical_evidence called: patient='tamara-chen-001', keyword='GI intolerance'
[INFO] 🔎 Found 1 matching notes for keyword='GI intolerance'
[INFO] ⚕️ generate_pa_justification called: patient='tamara-chen-001', medication='Ozempic (semaglutide 0.5mg)'
[INFO] 📋 PA analysis complete: step_therapy_met=False, exception_found=True
```

**Say:**
> "Three MCP tools fired in sequence. First it pulled Tamara's entire FHIR record. Then it hunted through her clinical notes for the GI intolerance evidence. Then it fed everything — the medical history, the policy text, the exception evidence — to GPT-4o-mini to reason over it and draft the letter."

---

## [2:30–3:00] The Endgame — The PA Letter

**Action:** Switch back to Prompt Opinion

**The agent's response should say:**
> *"Aetna requires a 6-month trial of Metformin. Tamara failed this step-therapy requirement — only 61 days completed.  However, I used the MCP Evidence Hunter and found a clinical note from Dr. Sarah Morrison documenting severe gastrointestinal intolerance that caused Metformin discontinuation. This constitutes a qualifying clinical exception under Aetna policy §4.2(b). I have bypassed the step-therapy requirement and drafted the attached Prior Authorization Exception Request."*

**Show the generated PA letter text.**

**Say:**
> "That's the Last Mile of healthcare AI. Not just a summary — a final, submittable document. This is what FHIR-native MCP interoperability looks like in practice. The Prompt Opinion agent called our local tools, got structured clinical data, and turned it into a real-world outcome. Thank you."

---

## Emergency Fallbacks

If Prompt Opinion agent doesn't connect:
→ Demo the REST API directly: `POST localhost:8000/tools/generate_pa_justification`

If ngrok tunnel drops:
→ Show the Streamlit dashboard and run the tool directly in the terminal:
```bash
curl -X POST http://localhost:8000/tools/generate_pa_justification \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "tamara-chen-001", "target_medication": "Ozempic", "policy_text": "Aetna requires 6 months metformin. Exception for GI intolerance."}'
```

If demo gods are against you:
→ Show the test suite running green: `pytest tests/ -v --ignore=tests/test_ui.py`
→ "All tests pass. The system works. Here's what it produces..." → show the test output
