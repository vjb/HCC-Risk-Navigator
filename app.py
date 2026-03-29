"""
app.py — HCC Risk Navigator Mock EHR Dashboard (Light Enterprise Theme)
"""
import os
import json
import streamlit as st
from datetime import date

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HCC Risk Navigator",
    page_icon="⚕️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# Premium Light Theme CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #f8fafc; /* Very soft cool gray background */
    color: #0f172a; /* Slate 900 for high-contrast text */
}

/* Hide Streamlit default branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Global Card Styling */
.glass-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    margin-bottom: 20px;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.glass-card:hover {
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04);
}

/* CFO Header Metrics */
.metric-value {
    font-size: 36px;
    font-weight: 700;
    line-height: 1.2;
}
.metric-label {
    font-size: 13px;
    font-weight: 600;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.text-blue { color: #2563eb; }
.text-green { color: #059669; }
.text-purple { color: #7c3aed; }

/* Patient Banner */
.patient-banner {
    background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
    color: white;
    border-radius: 12px;
    padding: 20px 28px;
    margin-bottom: 24px;
    box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.2);
}
.patient-name { font-size: 28px; font-weight: 700; margin-bottom: 4px; }
.patient-meta { font-size: 15px; color: #bfdbfe; font-weight: 400; }
.ins-badge {
    background: rgba(255, 255, 255, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.4);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    backdrop-filter: blur(4px);
}

/* Section Headers */
.section-title {
    font-size: 18px;
    font-weight: 600;
    color: #1e293b;
    border-bottom: 2px solid #f1f5f9;
    padding-bottom: 8px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Problem List Table */
.problem-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 0;
    border-bottom: 1px solid #f1f5f9;
}
.problem-row:last-child { border-bottom: none; }
.icd-pill {
    background: #eff6ff;
    color: #1d4ed8;
    padding: 4px 10px;
    border-radius: 6px;
    font-family: 'Courier New', monospace;
    font-weight: 700;
    font-size: 14px;
}
.hcc-pill {
    background: #fef3c7;
    color: #b45309;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
}

/* RAF Score Callout */
.raf-giant {
    font-size: 56px;
    font-weight: 800;
    color: #0f172a;
    text-align: center;
}

/* Clinical Notes & AI Highlights */
.note-box {
    background: #f8fafc;
    border-left: 4px solid #cbd5e1;
    padding: 16px;
    border-radius: 0 8px 8px 0;
    font-size: 14px;
    line-height: 1.6;
    color: #334155;
    white-space: pre-wrap;
}
.ai-highlight {
    background-color: #fef08a; /* Soft yellow */
    color: #854d0e;
    font-weight: 600;
    padding: 2px 4px;
    border-radius: 4px;
    border-bottom: 2px solid #f59e0b;
}

/* The AI Query Box */
.query-box {
    background: #f0fdf4;
    border: 1px solid #86efac;
    border-left: 5px solid #10b981;
    padding: 20px;
    border-radius: 8px;
    font-size: 14px;
    color: #065f46;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Data Loading & Helpers (Keep exactly the same as before)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_patient_data():
    try:
        from src.database import get_session
        from src.models import Patient, Condition, ClinicalNote
        session = get_session()
        patient = session.query(Patient).filter(Patient.name.contains("Tamara")).first()
        if not patient: return None, [], []
        conditions = session.query(Condition).filter_by(patient_id=patient.id).all()
        notes = session.query(ClinicalNote).filter_by(patient_id=patient.id).all()
        return patient, conditions, notes
    except Exception as e:
        return None, [], []

def apply_ai_highlight(text: str, keywords: list[str]) -> str:
    import re
    for kw in keywords:
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        text = pattern.sub(f'<span class="ai-highlight">{kw}</span>', text)
    return text

patient, conditions, notes = load_patient_data()

if not patient:
    st.error("⚠️ No patient data found. Run `python scripts/seed_db.py` first.")
    st.stop()

from src.hcc_engine import compute_raf
current_raf = compute_raf([c.icd10_code for c in conditions])
age = (date.today() - date.fromisoformat(patient.dob)).days // 365

# ─────────────────────────────────────────────────────────────────────────────
# 1. The CFO Header (Enterprise Macro Impact)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("### 🏢 Clinic-Wide Value-Based Care Performance (Trailing 30 Days)")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown('<div class="glass-card"><div class="metric-label">Charts Audited</div><div class="metric-value text-blue">1,402</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="glass-card"><div class="metric-label">HCC Gaps Found</div><div class="metric-value text-purple">184</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="glass-card"><div class="metric-label">Projected RAF Lift</div><div class="metric-value text-green">+ 42.50</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown('<div class="glass-card"><div class="metric-label">Potential Revenue Recovery</div><div class="metric-value text-green">$510,000</div></div>', unsafe_allow_html=True)

st.markdown("<hr style='border-top: 1px dashed #cbd5e1; margin: 10px 0 30px 0;'>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 2. Patient Banner
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="patient-banner">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <div class="patient-name">{patient.name}</div>
            <div class="patient-meta">DOB: {patient.dob} (Age {age}) • {patient.gender.title()} • MRN: {patient.fhir_id.split('-')[-1]}</div>
        </div>
        <div><span class="ins-badge">🛡️ {patient.insurance_plan}</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 3. Split View: Problem List & RAF Auditor
# ─────────────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown('<div class="section-title">📋 Coded Problem List (Active)</div>', unsafe_allow_html=True)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    for cond in conditions:
        hcc_badge = f'<span class="hcc-pill">HCC {cond.hcc_code} (+{cond.raf_weight:.3f})</span>' if cond.hcc_code else ''
        st.markdown(f"""
        <div class="problem-row">
            <div style="display:flex; align-items:center; gap:12px;">
                <span class="icd-pill">{cond.icd10_code}</span>
                <span style="font-weight:500;">{cond.description}</span>
            </div>
            {hcc_badge}
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col_right:
    st.markdown('<div class="section-title">📊 RAF Audit</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="glass-card" style="text-align:center;">
        <div class="metric-label">Current RAF Score</div>
        <div class="raf-giant">{current_raf:.3f}</div>
        <div style="font-size:14px; color:#64748b; margin-top:8px;">Base Revenue: ~${current_raf * 12000:,.0f} / yr</div>
    </div>
    """, unsafe_allow_html=True)

    audit_result = None
    if st.button("⚡ Execute AI Chart Audit", type="primary", use_container_width=True):
        with st.spinner("Hunting for uncoded clinical evidence..."):
            from src.hcc_engine import audit_hcc_gaps
            # Build context dictionary as before
            fhir_context = {
                "patient": {"fhir_id": patient.fhir_id, "name": patient.name, "dob": patient.dob, "gender": patient.gender, "insurance_plan": patient.insurance_plan},
                "conditions": [{"icd10_code": c.icd10_code, "description": c.description, "hcc_code": c.hcc_code, "raf_weight": c.raf_weight, "clinical_status": c.clinical_status} for c in conditions],
                "clinical_notes": [{"note_type": n.note_type, "authored_date": n.authored_date, "author": n.author, "content": n.content} for n in notes],
            }
            audit_result = audit_hcc_gaps(fhir_context)
            st.session_state["audit_result"] = audit_result

if "audit_result" in st.session_state:
    audit_result = st.session_state["audit_result"]

# ─────────────────────────────────────────────────────────────────────────────
# 4. The AI Insight Layer (Shows only after audit)
# ─────────────────────────────────────────────────────────────────────────────
if audit_result and audit_result.get("gaps"):
    st.markdown("<hr style='border-top: 1px dashed #cbd5e1; margin: 30px 0;'>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">🚨 AI Audit Findings & Revenue Gap</div>', unsafe_allow_html=True)
    
    gap = audit_result["gaps"][0] # Grab the first found gap
    
    col_note, col_action = st.columns([1.5, 1.5])
    
    with col_note:
        st.markdown(f"**Unstructured Clinical Note ({notes[0].authored_date})**")
        # Highlight the exact phrase the AI found
        highlighted_text = apply_ai_highlight(notes[0].content, [gap.get("evidence_quote", "burning sensation")])
        st.markdown(f'<div class="note-box">{highlighted_text}</div>', unsafe_allow_html=True)
        
    with col_action:
        rev_impact = gap.get("raf_delta", 0) * 12000
        st.markdown(f"""
        <div class="glass-card" style="border-left: 4px solid #f59e0b;">
            <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                <span style="font-weight:700; color:#b45309;">Missed HCC Opportunity</span>
                <span style="font-weight:700; color:#059669;">+ ${rev_impact:,.0f} / yr</span>
            </div>
            <div style="font-size:20px; font-weight:700; margin-bottom:4px;">{gap["suspected_icd10"]}</div>
            <div style="font-size:15px; color:#475569; margin-bottom:16px;">{gap["description"]} (HCC {gap["suspected_hcc"]})</div>
            <div style="font-size:13px; color:#64748b;"><strong>AI Rationale:</strong> {gap["clinical_rationale"]}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # The new "Last Mile" Clinician Query feature
        query_text = audit_result.get("draft_clinician_query", f"Dr. {notes[0].author}, your note indicates symptoms of diabetic neuropathy, but E11.40 is not on the active problem list. Do you agree to amend the chart?")
        st.markdown(f"""
        <div class="query-box">
            <div style="font-weight:700; margin-bottom:8px; display:flex; align-items:center; gap:6px;">
                <span>✉️</span> Auto-Generated Clinician Query
            </div>
            <em>"{query_text}"</em>
            <div style="margin-top: 16px;">
                <button style="background:#10b981; color:white; border:none; padding:8px 16px; border-radius:6px; cursor:pointer; font-weight:600; width:100%;">Send for Physician Sign-off</button>
            </div>
        </div>
        """, unsafe_allow_html=True)
elif audit_result:
    st.success("Audit complete. No coding gaps identified.")
else:
    # Show clean notes before audit
    st.markdown("<hr style='border-top: 1px dashed #cbd5e1; margin: 30px 0;'>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">📄 Clinical Documentation</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="note-box">{notes[0].content}</div>', unsafe_allow_html=True)
