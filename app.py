"""
app.py — HCC Risk Navigator Mock EHR Dashboard
================================================
Streamlit UI that displays:
  1. Tamara's patient banner (Medicare Advantage, age 68)
  2. Current coded problem list with HCC codes and RAF weights
  3. Aggregated current RAF score
  4. Clinical notes viewer with the HCC gap evidence highlighted
  5. "Run HCC Audit" button → calls the REST API → displays the gap report
"""
import os
import time
import json
import requests
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session

# ─────────────────────────────────────────────────────────────────────────────
# Page config (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HCC Risk Navigator | Mock EHR",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# Styling
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Dark clinical theme */  
.stApp {
    background: #0a0e1a;
    color: #e2e8f0;
}

/* Patient banner */
.patient-banner {
    background: linear-gradient(135deg, #1a2035 0%, #0f172a 100%);
    border: 1px solid #2d3748;
    border-left: 4px solid #3b82f6;
    border-radius: 12px;
    padding: 20px 28px;
    margin-bottom: 24px;
}

.patient-name {
    font-size: 26px;
    font-weight: 700;
    color: #f1f5f9;
    margin: 0 0 4px 0;
}

.patient-meta {
    font-size: 14px;
    color: #94a3b8;
    margin: 0;
}

.ins-badge {
    background: #1e3a5f;
    color: #60a5fa;
    border: 1px solid #2563eb;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
}

/* Section headers */
.section-header {
    font-size: 13px;
    font-weight: 600;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #1e293b;
}

/* RAF score card */
.raf-card {
    background: #111827;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 18px 22px;
    text-align: center;
}

.raf-score {
    font-size: 42px;
    font-weight: 700;
    color: #f59e0b;
    line-height: 1;
}

.raf-label {
    font-size: 12px;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 6px;
}

.raf-projected {
    font-size: 28px;
    font-weight: 700;
    color: #10b981;
    line-height: 1;
}

/* Problem list table */
.condition-row {
    background: #111827;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 16px;
}

.icd-code {
    background: #1e293b;
    color: #93c5fd;
    border-radius: 6px;
    padding: 4px 10px;
    font-family: 'Courier New', monospace;
    font-size: 13px;
    font-weight: 600;
    min-width: fit-content;
}

.hcc-badge {
    background: #312e81;
    color: #a5b4fc;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

.raf-badge {
    background: #1a2e1a;
    color: #86efac;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

/* Clinical notes */
.note-card {
    background: #111827;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 12px;
    position: relative;
}

.note-header {
    font-size: 12px;
    color: #64748b;
    margin-bottom: 12px;
    display: flex;
    gap: 12px;
}

.note-content {
    font-size: 13px;
    color: #cbd5e1;
    line-height: 1.7;
    white-space: pre-wrap;
    font-family: 'Inter', sans-serif;
}

.note-badge {
    background: #1e293b;
    color: #94a3b8;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
}

/* HCC Gap alert */
.gap-card {
    background: linear-gradient(135deg, #1a0f2e 0%, #0f172a 100%);
    border: 1px solid #7c3aed;
    border-left: 4px solid #8b5cf6;
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 12px;
}

.gap-icd {
    font-size: 20px;
    font-weight: 700;
    color: #c4b5fd;
    font-family: 'Courier New', monospace;
}

.gap-description {
    font-size: 14px;
    color: #e2e8f0;
    margin-top: 4px;
}

.evidence-quote {
    background: #1e1b4b;
    border-left: 3px solid #6366f1;
    border-radius: 4px;
    padding: 10px 14px;
    font-size: 13px;
    color: #a5b4fc;
    font-style: italic;
    margin: 12px 0;
}

.confidence-high { color: #10b981; font-weight: 600; }
.confidence-medium { color: #f59e0b; font-weight: 600; }
.confidence-low { color: #ef4444; font-weight: 600; }

/* Summary box */
.summary-box {
    background: #0f2027;
    border: 1px solid #1e4d2e;
    border-radius: 8px;
    padding: 14px 18px;
    font-size: 14px;
    color: #86efac;
    line-height: 1.6;
}

/* Revenue impact */
.revenue-card {
    background: linear-gradient(135deg, #1a2e1a 0%, #0f1f0f 100%);
    border: 1px solid #166534;
    border-radius: 10px;
    padding: 18px 22px;
    text-align: center;
}

.revenue-amount {
    font-size: 36px;
    font-weight: 700;
    color: #4ade80;
}

.divider {
    border: none;
    border-top: 1px solid #1e293b;
    margin: 28px 0;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Data loading helpers
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource
def get_db_session():
    from src.database import get_session
    return get_session()


@st.cache_data(ttl=30)
def load_patient_data():
    """Load Tamara's data from SQLite."""
    try:
        from src.database import get_session
        from src.models import Patient, Condition, ClinicalNote
        session = get_session()
        patient = session.query(Patient).filter(Patient.name.contains("Tamara")).first()
        if not patient:
            return None, [], []
        conditions = session.query(Condition).filter_by(patient_id=patient.id).all()
        notes = session.query(ClinicalNote).filter_by(patient_id=patient.id).all()
        return patient, conditions, notes
    except Exception as e:
        st.error(f"Database error: {e}")
        return None, [], []


def highlight_evidence(text: str, keywords: list[str]) -> str:
    """Wrap evidence keywords in a highlight span."""
    import re
    for kw in keywords:
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        text = pattern.sub(f'<mark style="background:#3b1d61;color:#c4b5fd;border-radius:3px;padding:1px 3px;">{kw}</mark>', text)
    return text


# ─────────────────────────────────────────────────────────────────────────────
# Load data
# ─────────────────────────────────────────────────────────────────────────────

patient, conditions, notes = load_patient_data()

if not patient:
    st.error("⚠️  No patient data found. Run `python scripts/seed_db.py` first.")
    st.stop()

from src.hcc_engine import compute_raf, HCC_MAP
current_raf = compute_raf([c.icd10_code for c in conditions])
from datetime import date
dob = date.fromisoformat(patient.dob)
age = (date.today() - dob).days // 365


# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("## 🏥 HCC Risk Navigator")
st.markdown('<p style="color:#64748b;font-size:14px;margin-top:-10px;">Clinical Documentation Improvement · Medicare Advantage Risk Adjustment Audit</p>', unsafe_allow_html=True)

st.markdown('<div class="section-header" style="margin-top: 24px;">🏢 Clinic-Wide Impact (YTD)</div>', unsafe_allow_html=True)
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("Total Patients Audited", "1,402")
col_m2.metric("HCC Gaps Identified", "184")
col_m3.metric("Projected RAF Increase", "+42.5", delta="Trending Up")
col_m4.metric("Potential Revenue", "$510,000", delta="+12%")
st.markdown("<br>", unsafe_allow_html=True)

# Patient Banner
st.markdown(f"""
<div class="patient-banner">
    <div style="display:flex;align-items:flex-start;justify-content:space-between;">
        <div>
            <div class="patient-name">{patient.name}</div>
            <div class="patient-meta" style="margin-top:6px;">
                DOB: {patient.dob} &nbsp;·&nbsp; Age: {age} &nbsp;·&nbsp; {patient.gender.title()} &nbsp;·&nbsp; ID: {patient.fhir_id}
            </div>
        </div>
        <div style="text-align:right;">
            <span class="ins-badge">🛡 {patient.insurance_plan}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Main layout: Problem List | RAF Score | Run Audit
# ─────────────────────────────────────────────────────────────────────────────

col_problems, col_raf, col_audit = st.columns([3, 1.5, 1.5])

with col_problems:
    st.markdown('<div class="section-header">📋 Active Problem List (Coded ICD-10)</div>', unsafe_allow_html=True)
    for cond in conditions:
        hcc_info = HCC_MAP.get(cond.icd10_code, {})
        hcc_text = f"HCC {cond.hcc_code}" if cond.hcc_code else "Non-HCC"
        raf_text = f"RAF +{cond.raf_weight:.3f}" if cond.raf_weight else "RAF 0.000"
        st.markdown(f"""
        <div class="condition-row">
            <span class="icd-code">{cond.icd10_code}</span>
            <span style="flex:1;font-size:14px;color:#e2e8f0;">{cond.description}</span>
            <span class="hcc-badge">{hcc_text}</span>
            <span class="raf-badge">{raf_text}</span>
        </div>
        """, unsafe_allow_html=True)

with col_raf:
    st.markdown('<div class="section-header">📊 RAF Score</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="raf-card">
        <div class="raf-score">{current_raf:.3f}</div>
        <div class="raf-label">Current RAF</div>
        <hr style="border-color:#1e293b;margin:12px 0;">
        <div style="font-size:11px;color:#64748b;">HCC Codes Captured</div>
        <div style="font-size:22px;font-weight:700;color:#60a5fa;margin-top:4px;">
            {sum(1 for c in conditions if c.hcc_code and c.hcc_code > 0)}
        </div>
        <div style="font-size:11px;color:#64748b;margin-top:8px;">Annual Revenue</div>
        <div style="font-size:18px;font-weight:600;color:#f59e0b;margin-top:2px;">
            ~${current_raf * 12000:,.0f}
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_audit:
    st.markdown('<div class="section-header">🔍 HCC Audit</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:13px;color:#94a3b8;margin-bottom:16px;">Run the AI engine to scan for uncoded HCC conditions in the clinical notes.</div>', unsafe_allow_html=True)

    audit_result = None
    if st.button("⚡ Run HCC Audit", type="primary", use_container_width=True):
        with st.spinner("Analyzing clinical documentation..."):
            try:
                from unittest.mock import patch
                from src.hcc_engine import audit_hcc_gaps

                # Build context in-app for demo reliability
                fhir_context = {
                    "patient": {
                        "fhir_id": patient.fhir_id,
                        "name": patient.name,
                        "dob": patient.dob,
                        "gender": patient.gender,
                        "insurance_plan": patient.insurance_plan,
                    },
                    "conditions": [
                        {"icd10_code": c.icd10_code, "description": c.description,
                         "hcc_code": c.hcc_code, "raf_weight": c.raf_weight,
                         "clinical_status": c.clinical_status}
                        for c in conditions
                    ],
                    "clinical_notes": [
                        {"note_type": n.note_type, "authored_date": n.authored_date,
                         "author": n.author, "content": n.content}
                        for n in notes
                    ],
                }
                audit_result = audit_hcc_gaps(fhir_context)
                st.session_state["audit_result"] = audit_result
                st.success(f"✅ Audit complete — {audit_result['gap_count']} gap(s) found")
            except Exception as e:
                st.error(f"Audit error: {e}")

    if "audit_result" in st.session_state and st.session_state["audit_result"]:
        audit_result = st.session_state["audit_result"]


# ─────────────────────────────────────────────────────────────────────────────
# Clinical Notes
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown('<div class="section-header">📝 Clinical Documentation (FHIR DocumentReference)</div>', unsafe_allow_html=True)

evidence_keywords = ["burning sensation", "numbness", "gabapentin", "neuropathy", "bilateral lower extremity", "peripheral neuropathy"]

for note in notes:
    highlighted = highlight_evidence(note.content, evidence_keywords)
    st.markdown(f"""
    <div class="note-card">
        <div class="note-header">
            <span class="note-badge">📄 {note.note_type}</span>
            <span class="note-badge">📅 {note.authored_date}</span>
            <span class="note-badge">👩‍⚕️ {note.author or 'Unknown'}</span>
        </div>
        <div class="note-content">{highlighted}</div>
    </div>
    """, unsafe_allow_html=True)

    if audit_result and audit_result.get("gaps"):
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin-top:8px;margin-bottom:4px;">
            <span style="font-size:13px;color:#8b5cf6;font-weight:600;">⬆ HCC Gap Evidence</span>
            <span style="font-size:11px;color:#64748b;">Highlighted text supports the uncoded condition</span>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# HCC Gap Report (shown after audit)
# ─────────────────────────────────────────────────────────────────────────────

if audit_result:
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">🚨 HCC Coding Gap Analysis — AI Audit Report</div>', unsafe_allow_html=True)

    if audit_result.get("audit_summary"):
        st.markdown(f"""
        <div class="summary-box">
            🤖 <strong>AI Summary:</strong> {audit_result["audit_summary"]}
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    for gap in audit_result.get("gaps", []):
        conf = gap.get("confidence", "MEDIUM")
        conf_class = f"confidence-{conf.lower()}"
        hcc = HCC_MAP.get(gap["suspected_icd10"], {})
        raf_delta = gap.get("raf_delta", hcc.get("raf", 0))
        revenue_delta = raf_delta * 12000

        st.markdown(f"""
        <div class="gap-card">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;">
                <div>
                    <span class="gap-icd">{gap["suspected_icd10"]}</span>
                    <div class="gap-description">{gap.get("description", "")}</div>
                </div>
                <div style="text-align:right;">
                    <span class="hcc-badge">HCC {gap.get("suspected_hcc", "?")}</span>
                    <span class="raf-badge" style="margin-left:4px;">+{raf_delta:.3f} RAF</span>
                    <div class="{conf_class}" style="font-size:12px;margin-top:4px;">⭐ {conf} confidence</div>
                </div>
            </div>
            <div class="evidence-quote">
                💬 "{gap.get("evidence_quote", "")}"
            </div>
            <div style="font-size:13px;color:#94a3b8;margin-top:8px;">
                <strong style="color:#c4b5fd;">Clinical Rationale:</strong> {gap.get("clinical_rationale", "")}
            </div>
        </div>
        """, unsafe_allow_html=True)

        if gap.get("draft_clinician_query"):
            st.info(f"**Draft Clinician Query:**\n\n{gap['draft_clinician_query']}", icon="✍️")

        col_rev1, col_rev2, col_rev3 = st.columns(3)
        with col_rev1:
            st.metric("Current RAF", f"{audit_result['current_raf']:.3f}")
        with col_rev2:
            st.metric("Projected RAF", f"{audit_result['projected_raf']:.3f}",
                      delta=f"+{audit_result['raf_delta']:.3f}")
        with col_rev3:
            st.metric("Est. Revenue Impact", f"${revenue_delta:,.0f}/yr",
                      delta="per patient", delta_color="normal")


# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;font-size:12px;color:#374151;">
    HCC Risk Navigator · Mock EHR Dashboard · Data is entirely synthetic (HIPAA-safe) · 
    CMS HCC Model V28 · MCP Server running at <code>localhost:8000/mcp/sse</code>
</div>
""", unsafe_allow_html=True)
