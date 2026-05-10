# FIRE: Hackathon Demo Script (3-Minute Maximum)

**General Advice for the Video:** 
- Keep a brisk, energetic pace. Do not read the slides word-for-word; speak *to* them. 
- During the live demo, pre-type or quickly copy/paste the prompts. If the agents take a few seconds to "think", use that dead air to explain *why* they are thinking (e.g., "Right now, it's cross-referencing PubMed...").

---

## Part 1: The Pitch (0:00 - 1:00)
*(Screen: Presenting `FIRE_Revenue_Recovery.pdf` Slides 1 to 7)*

**[Slide 1: Title]**
"Hi everyone, this is FIRE: The FHIR-Integrated Revenue Engine. We built a deterministic, multi-agent pipeline to solve the 'Last Mile' of healthcare AI: recovering lost Medicare revenue."

**[Slide 2: The Problem]**
"Under the new CMS V28 risk-adjustment model, generic diagnoses are now worth zero dollars. Hospitals are losing millions simply because specific conditions are buried in unstructured clinical notes."

**[Slide 3 & 4: The Broken Status Quo & The Solution]**
"You can't hire enough humans to read 10,000 patient charts a day. Enter FIRE. We deploy an orchestrated team of specialist AI agents directly onto your FHIR server to autonomously triage patients, identify gaps, and draft verified billing queries."

**[Slide 5: Architecture]**
"We built both a FastMCP tool and a 3-agent A2A topology. The Orchestrator pulls the raw FHIR data, the Risk Navigator acts as the analyst, and the Compliance Reviewer acts as a compliance validator."

**[Slide 6: Security]**
"We solved the trust problem. FIRE uses Prompt Opinion's SHARP protocols to natively handle EHR credentials without rogue API keys. And to prevent LLM hallucinations, every proposed code is strictly grounded in PubMed and CMS M.E.A.T. standards."

---

## Part 2: The Live Demo (1:00 - 2:30)
*(Screen: Switch to the Prompt Opinion platform workspace)*

"Let me show you how it works. Note that while this can be entirely automated, we are running it step-by-step to show you under the hood."

**[Demo Step 1: Baseline]**
*(Paste Prompt 1 into the chat)*
"First, the Clinical Orchestrator connects to our live MCP server to triage the patient cohort. It calculates the current RAF baseline mathematically (zero LLMs involved) and flags three patients who have unreviewed clinical notes attached to their FHIR records."

**[Demo Step 2: Gap Analysis]**
*(Paste Prompt 2 into the chat)*
"Next, we pass the flagged notes to the Risk Navigator. The Navigator cross-references the clinical text against the CMS guidelines. Notice how it isolates Tamara, Richard, and Maria, identifying the exact ICD-10 codes and citing the clinical evidence to prove each gap."

**[Demo Step 3: RAF Impact Calculation]**
*(Paste Prompt 3 into the chat)*
"We can then ask the engine to calculate the total RAF impact. It deterministically sums the deltas, giving us the exact financial value of these discovered gaps across the cohort."

**[Demo Step 4: Compliance]**
*(Paste Prompt 4 into the chat)*
"Now for the Last Mile. We pass these findings to the Compliance Reviewer. It acts as an internal auditor, verifying that the proposed treatments legitimately match the diagnosis via PubMed, and ensuring strict CMS M.E.A.T. criteria are met. Look at those green checkmarks: zero hallucinations, fully verified."

**[Demo Step 5: System Hand-off]**
*(Paste Prompt 5 into the chat)*
"Finally, we don't just output a summary. FIRE generates a highly-structured JSON payload (matching the EPIC HCLS model format) so we can instantly POST these tasks to an enterprise RCM engine."

---

## Part 3: The Close (2:30 - 3:00)
*(Screen: Switch back to Slide 7)*

**[Slide 7: The Financial ROI]**
"Because this pipeline is deterministic, it scales infinitely with zero upfront cost. If we deploy this to a single mid-sized hospital with 10,000 patients and find just a 5% gap prevalence, that's $1,000,000 in recovered annual revenue. On our 10% shared savings model, that is $100,000 in ARR for us per hospital."

**[Slide 8: The Vision]**
"This is the endgame of healthcare AI. We aren't just summarizing text: we are using Prompt Opinion to route authenticated clinical data into actionable financial workflows. Thank you."
