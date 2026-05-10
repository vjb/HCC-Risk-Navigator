# 🔥 FIRE: Hackathon Demo Script (3 Minutes)
*This script is designed to be spoken naturally while the sped-up WebP video of the 4-step execution plays in the background.*

---

### [0:00 - 0:30] Introduction: The V28 Problem & The Solution
**Visual:** The Prompt Opinion platform is open. The user types the first prompt.
**Audio:**
"Hospitals are currently losing millions of dollars in Medicare revenue because their clinical documentation isn't specific enough to meet the new, incredibly strict CMS V28 requirements. 

Enter FIRE: The FHIR-Integrated Revenue Engine. 

FIRE is a deterministic, multi-agent AI pipeline that directly interfaces with live FHIR R4 servers to automatically audit patient records for undocumented coding gaps. We use the Prompt Opinion 'Agents Assemble' framework and the SHARP protocol to ensure we are fully compliant with Darena Health and HTI-1 mandates. This means FIRE can plug into any compliant EHR instantly."

---

### [0:30 - 1:00] Step 1: The Cohort Scorecard & Financial Impact
**Visual:** The Orchestrator runs the `audit_v28_cohort` tool and returns the markdown table.
**Audio:**
"Let's see it in action. Our first step is the Cohort Sweep. 

Our Clinical Orchestrator agent reaches out via our custom MCP backend to a live, public HAPI FHIR server—no fake mock data here. It pulls a block of patients and immediately generates a 'RAF Gap Scorecard.' 

We do this to show the financial impact first. Using the industry standard of $10,000 per RAF point, you can clearly see the baseline revenue for each patient and identify exactly who needs a clinical documentation review based on the presence of unstructured notes."

---

### [1:00 - 1:45] Step 2: Risk Analysis (Deterministic Handoff)
**Visual:** The user pastes the second prompt, passing data to the 'HCC Risk Navigator'.
**Audio:**
"Next, we move to Risk Analysis. This is where our architecture shines. 

Instead of letting the LLM summarize data and risk hallucinations, our Orchestrator passes the *entire raw JSON array* in a single, deterministic hand-off to our second agent: the HCC Risk Navigator. 

The Risk Navigator acts as our specialized analyst. It cross-references the raw clinical notes against the V28 HCC dictionary. Here, you can see it successfully found hidden, high-value gaps for Tamara, Richard, and Maria—calculating the exact projected RAF increases and the precise financial impact for each."

---

### [1:45 - 2:15] Step 3: The Zero-Trust Compliance Firewall
**Visual:** The user pastes the third prompt, passing data to the 'Compliance Reviewer'.
**Audio:**
"But finding a gap isn't enough; you have to legally prove it. So, we pass these findings to our third agent: The Compliance Reviewer. 

This agent acts as a zero-trust firewall. It has no direct access to the FHIR database. Its sole purpose is to act as an auditor to prevent fraud. It rigorously verifies that every proposed ICD-10 code is backed by strict CMS M.E.A.T. criteria—meaning the doctor explicitly Monitored, Evaluated, Assessed, or Treated the condition in the text. 

As you can see, all three findings have been verified and approved."

---

### [2:15 - 3:00] Step 4: The Deliverable & Business Model
**Visual:** The final 5Ts report generates, showing the total revenue and the Physician Query drafts.
**Audio:**
"Finally, we compile this into a complete, professional deliverable. The engine generates fully customized Physician Query drafts ready to be signed, recovering a massive $9,540 in immediate revenue across just three patients.

Our business model is simple: We charge minimal upfront SaaS fees and take exactly 10% of the net new revenue generated. 

With a conservative estimate of finding just a 5% gap prevalence in a mid-sized hospital, FIRE generates $100,000 in Annual Recurring Revenue per hospital. Capturing just 10 hospitals makes FIRE a $1 Million ARR business with near-zero marginal costs. 

That is the power of the FHIR-Integrated Revenue Engine."
