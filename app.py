"""
app.py — HCC Risk Navigator | Clinical Intelligence Platform
"""
import re
import streamlit as st
from datetime import date

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HCC Risk Navigator | Clinical Intelligence",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS — Enterprise Clinical Platform
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Reset & Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background-color: #f0f2f5;
    color: #1a2332;
    -webkit-font-smoothing: antialiased;
}

/* ── Streamlit chrome removal ── */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }

/* ── Application chrome ── */
.app-header {
    background: #0f2044;
    margin: -1rem -1rem 0 -1rem;
    padding: 14px 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 3px solid #1a56db;
}
.app-header-brand {
    font-size: 15px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}
.app-header-sub {
    font-size: 12px;
    font-weight: 400;
    color: #7ea6e0;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-top: 2px;
}
.app-header-right {
    font-size: 12px;
    color: #7ea6e0;
    text-align: right;
}

/* ── Page section wrapper ── */
.page-body {
    padding: 24px 8px 0 8px;
}

/* ── KPI strip ── */
.kpi-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1px;
    background: #d1d9e6;
    border: 1px solid #d1d9e6;
    border-radius: 6px;
    overflow: hidden;
    margin-bottom: 24px;
}
.kpi-cell {
    background: #ffffff;
    padding: 20px 24px;
}
.kpi-label {
    font-size: 11px;
    font-weight: 600;
    color: #6b7a99;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 8px;
}
.kpi-value {
    font-size: 32px;
    font-weight: 700;
    line-height: 1;
    color: #0f2044;
}
.kpi-value.accent-blue   { color: #1a56db; }
.kpi-value.accent-violet { color: #5b21b6; }
.kpi-value.accent-teal   { color: #0d7490; }
.kpi-value.accent-green  { color: #047857; }
.kpi-delta {
    font-size: 12px;
    color: #6b7a99;
    margin-top: 6px;
}

/* ── Divider ── */
.section-divider {
    height: 1px;
    background: #d1d9e6;
    margin: 20px 0 28px 0;
}

/* ── Patient banner ── */
.patient-banner {
    background: #0f2044;
    border-radius: 6px;
    padding: 18px 28px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.patient-name {
    font-size: 22px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.01em;
}
.patient-meta {
    font-size: 13px;
    color: #93b8e8;
    margin-top: 4px;
    font-weight: 400;
}
.patient-meta span {
    margin: 0 10px;
    color: #4a6fa5;
}
.patient-meta span:first-child { margin-left: 0; }
.coverage-badge {
    background: #1a3a6e;
    border: 1px solid #2a5aaa;
    color: #93b8e8;
    font-size: 11px;
    font-weight: 600;
    padding: 5px 14px;
    border-radius: 3px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

/* ── Section heading ── */
.section-heading {
    font-size: 11px;
    font-weight: 700;
    color: #6b7a99;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding-bottom: 10px;
    border-bottom: 2px solid #e2e7f0;
    margin-bottom: 0;
}

/* ── Card ── */
.card {
    background: #ffffff;
    border: 1px solid #d1d9e6;
    border-radius: 6px;
    overflow: hidden;
}
.card-body { padding: 0; }

/* ── Problem list table ── */
.prob-table {
    width: 100%;
    border-collapse: collapse;
}
.prob-table th {
    background: #f7f9fc;
    font-size: 10px;
    font-weight: 700;
    color: #6b7a99;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    padding: 10px 16px;
    text-align: left;
    border-bottom: 1px solid #e2e7f0;
}
.prob-table td {
    padding: 13px 16px;
    font-size: 13.5px;
    color: #1a2332;
    border-bottom: 1px solid #f0f2f5;
    vertical-align: middle;
}
.prob-table tr:last-child td { border-bottom: none; }
.prob-table tr:hover td { background: #f7f9fc; }
.code-tag {
    font-family: 'SF Mono', 'Fira Code', 'Courier New', monospace;
    font-size: 12px;
    font-weight: 700;
    color: #1a56db;
    background: #eff4ff;
    border: 1px solid #c7d7fd;
    padding: 3px 8px;
    border-radius: 3px;
    display: inline-block;
}
.hcc-tag {
    font-size: 11px;
    font-weight: 600;
    color: #6b4c00;
    background: #fef9ec;
    border: 1px solid #f5d76e;
    padding: 2px 8px;
    border-radius: 3px;
    display: inline-block;
}
.status-active {
    font-size: 11px;
    font-weight: 600;
    color: #065f46;
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
    padding: 2px 8px;
    border-radius: 3px;
    display: inline-block;
}

/* ── RAF score panel ── */
.raf-panel {
    background: #ffffff;
    border: 1px solid #d1d9e6;
    border-radius: 6px;
    padding: 28px 20px;
    text-align: center;
    margin-bottom: 16px;
}
.raf-score-label {
    font-size: 10px;
    font-weight: 700;
    color: #6b7a99;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 10px;
}
.raf-score-value {
    font-size: 52px;
    font-weight: 800;
    color: #0f2044;
    line-height: 1;
    letter-spacing: -0.02em;
}
.raf-revenue {
    font-size: 13px;
    color: #6b7a99;
    margin-top: 10px;
    border-top: 1px solid #e2e7f0;
    padding-top: 10px;
}

/* ── Audit run button override ── */
div[data-testid="stButton"] button {
    background: #1a56db !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 4px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em !important;
    padding: 10px 20px !important;
    transition: background 0.15s ease !important;
    box-shadow: none !important;
}
div[data-testid="stButton"] button:hover {
    background: #1648c0 !important;
}

/* ── Clinical note ── */
.note-header {
    background: #f7f9fc;
    border-bottom: 1px solid #e2e7f0;
    padding: 10px 16px;
    font-size: 11px;
    font-weight: 700;
    color: #6b7a99;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}
.note-body {
    padding: 16px;
    font-size: 13.5px;
    line-height: 1.7;
    color: #2d3748;
    white-space: pre-wrap;
    font-family: 'Georgia', 'Times New Roman', serif;
}
.evidence-mark {
    background: #fef08a;
    color: #713f12;
    font-weight: 700;
    padding: 1px 3px;
    border-radius: 2px;
    border-bottom: 2px solid #eab308;
}

/* ── Findings panel ── */
.finding-panel {
    background: #ffffff;
    border: 1px solid #d1d9e6;
    border-left: 3px solid #d97706;
    border-radius: 6px;
    margin-bottom: 14px;
    overflow: hidden;
}
.finding-header {
    background: #fffbeb;
    border-bottom: 1px solid #fde68a;
    padding: 10px 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.finding-label {
    font-size: 11px;
    font-weight: 700;
    color: #92400e;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}
.finding-revenue {
    font-size: 14px;
    font-weight: 700;
    color: #047857;
}
.finding-body {
    padding: 14px 16px;
}
.finding-icd {
    font-size: 18px;
    font-weight: 700;
    color: #0f2044;
    font-family: 'SF Mono', 'Fira Code', monospace;
    margin-bottom: 2px;
}
.finding-desc {
    font-size: 14px;
    color: #374151;
    margin-bottom: 10px;
}
.finding-rationale {
    font-size: 12.5px;
    color: #6b7a99;
    line-height: 1.5;
    background: #f7f9fc;
    padding: 10px 12px;
    border-radius: 4px;
    border-left: 2px solid #d1d9e6;
}
.finding-rationale strong { color: #374151; }

/* ── Clinician query ── */
.query-panel {
    background: #ffffff;
    border: 1px solid #d1d9e6;
    border-left: 3px solid #1a56db;
    border-radius: 6px;
    overflow: hidden;
}
.query-header {
    background: #eff4ff;
    border-bottom: 1px solid #c7d7fd;
    padding: 10px 16px;
    font-size: 11px;
    font-weight: 700;
    color: #1e40af;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}
.query-body {
    padding: 14px 16px;
    font-size: 13.5px;
    color: #1e3a5f;
    line-height: 1.6;
    font-style: italic;
}
.query-action {
    background: #f7f9fc;
    border-top: 1px solid #e2e7f0;
    padding: 12px 16px;
}
.query-btn {
    background: #1a56db;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 18px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    letter-spacing: 0.03em;
    width: 100%;
    transition: background 0.15s;
}
.query-btn:hover { background: #1648c0; }

/* ── Audit findings section title ── */
.findings-section-bar {
    background: #fff7ed;
    border: 1px solid #fde68a;
    border-left: 3px solid #d97706;
    padding: 10px 16px;
    border-radius: 4px;
    margin-bottom: 16px;
    font-size: 12px;
    font-weight: 700;
    color: #92400e;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}

/* ── Success state ── */
.audit-success {
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
    border-left: 3px solid #047857;
    padding: 12px 16px;
    border-radius: 4px;
    font-size: 13px;
    color: #065f46;
    font-weight: 500;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_patient_data():
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
    except Exception:
        return None, [], []


def apply_evidence_highlight(text: str, keywords: list) -> str:
    for kw in keywords:
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        text = pattern.sub(f'<mark class="evidence-mark">{kw}</mark>', text)
    return text


# ─────────────────────────────────────────────────────────────────────────────
# Data
# ─────────────────────────────────────────────────────────────────────────────
patient, conditions, notes = load_patient_data()

if not patient:
    st.error("No patient data found. Run `python scripts/seed_db.py` to seed the database.")
    st.stop()

from src.hcc_engine import compute_raf
current_raf = compute_raf([c.icd10_code for c in conditions])
age = (date.today() - date.fromisoformat(patient.dob)).days // 365

# ─────────────────────────────────────────────────────────────────────────────
# Application Header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <div>
        <div class="app-header-brand">HCC Risk Navigator</div>
        <div class="app-header-sub">Clinical Intelligence Platform &nbsp;|&nbsp; Medicare Advantage RAF Optimization</div>
    </div>
    <div class="app-header-right">
        Mock EHR &nbsp;&bull;&nbsp; CMS CY2024 Coding Guidelines
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# KPI Strip
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div style="font-size:11px; font-weight:700; color:#6b7a99; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:10px;">Clinic-Wide Performance &mdash; Trailing 30 Days</div>', unsafe_allow_html=True)
st.markdown("""
<div class="kpi-strip">
    <div class="kpi-cell">
        <div class="kpi-label">Charts Audited</div>
        <div class="kpi-value accent-blue">1,402</div>
        <div class="kpi-delta">+18% vs prior period</div>
    </div>
    <div class="kpi-cell">
        <div class="kpi-label">HCC Gaps Identified</div>
        <div class="kpi-value accent-violet">184</div>
        <div class="kpi-delta">13.1% gap rate</div>
    </div>
    <div class="kpi-cell">
        <div class="kpi-label">Projected RAF Lift</div>
        <div class="kpi-value accent-teal">+42.50</div>
        <div class="kpi-delta">Across open gap population</div>
    </div>
    <div class="kpi-cell">
        <div class="kpi-label">Potential Revenue Recovery</div>
        <div class="kpi-value accent-green">$510,000</div>
        <div class="kpi-delta">Annualized estimate</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Patient Banner
# ─────────────────────────────────────────────────────────────────────────────
mrn = patient.fhir_id.split('-')[-1].upper()
st.markdown(f"""
<div class="patient-banner">
    <div>
        <div class="patient-name">{patient.name}</div>
        <div class="patient-meta">
            DOB: {patient.dob}
            <span>|</span>
            Age {age}
            <span>|</span>
            {patient.gender.title()}
            <span>|</span>
            MRN: {mrn}
        </div>
    </div>
    <div>
        <span class="coverage-badge">{patient.insurance_plan}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Split: Problem List + RAF Auditor
# ─────────────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([2, 1], gap="medium")

with col_left:
    st.markdown('<div class="section-heading">Active Problem List</div>', unsafe_allow_html=True)
    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

    rows_html = ""
    for cond in conditions:
        status_html = '<span class="status-active">Active</span>'
        hcc_html = (
            f'<span class="hcc-tag">HCC {cond.hcc_code} &nbsp;+{cond.raf_weight:.3f}</span>'
            if cond.hcc_code else
            '<span style="color:#9ca3af; font-size:12px;">—</span>'
        )
        rows_html += f"""
        <tr>
            <td><span class="code-tag">{cond.icd10_code}</span></td>
            <td style="font-weight:500;">{cond.description}</td>
            <td>{hcc_html}</td>
            <td>{status_html}</td>
        </tr>
        """

    st.markdown(f"""
    <div class="card">
        <table class="prob-table">
            <thead>
                <tr>
                    <th>ICD-10</th>
                    <th>Description</th>
                    <th>HCC / RAF Weight</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)

with col_right:
    st.markdown('<div class="section-heading">RAF Score Audit</div>', unsafe_allow_html=True)
    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="raf-panel">
        <div class="raf-score-label">Current RAF Score</div>
        <div class="raf-score-value">{current_raf:.3f}</div>
        <div class="raf-revenue">Estimated Base Revenue &nbsp;&bull;&nbsp; ${current_raf * 12000:,.0f} / yr</div>
    </div>
    """, unsafe_allow_html=True)

    audit_result = None
    if st.button("Run AI Chart Audit", type="primary", use_container_width=True):
        with st.spinner("Analyzing clinical documentation for uncoded HCC conditions..."):
            from src.hcc_engine import audit_hcc_gaps
            fhir_context = {
                "patient": {
                    "fhir_id": patient.fhir_id,
                    "name": patient.name,
                    "dob": patient.dob,
                    "gender": patient.gender,
                    "insurance_plan": patient.insurance_plan,
                },
                "conditions": [
                    {
                        "icd10_code": c.icd10_code,
                        "description": c.description,
                        "hcc_code": c.hcc_code,
                        "raf_weight": c.raf_weight,
                        "clinical_status": c.clinical_status,
                    }
                    for c in conditions
                ],
                "clinical_notes": [
                    {
                        "note_type": n.note_type,
                        "authored_date": n.authored_date,
                        "author": n.author,
                        "content": n.content,
                    }
                    for n in notes
                ],
            }
            audit_result = audit_hcc_gaps(fhir_context)
            st.session_state["audit_result"] = audit_result

if "audit_result" in st.session_state:
    audit_result = st.session_state["audit_result"]

# ─────────────────────────────────────────────────────────────────────────────
# AI Audit Findings
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

if audit_result and audit_result.get("gaps"):
    st.markdown('<div class="findings-section-bar">Audit Findings &mdash; Uncoded HCC Opportunities</div>', unsafe_allow_html=True)

    gap = audit_result["gaps"][0]
    col_note, col_action = st.columns([1, 1], gap="medium")

    with col_note:
        st.markdown('<div class="section-heading">Source Clinical Documentation</div>', unsafe_allow_html=True)
        st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
        highlighted = apply_evidence_highlight(
            notes[0].content,
            [gap.get("evidence_quote", "")]
        )
        st.markdown(f"""
        <div class="card">
            <div class="note-header">
                {notes[0].note_type} &nbsp;&bull;&nbsp; {notes[0].authored_date} &nbsp;&bull;&nbsp; {notes[0].author}
            </div>
            <div class="note-body">{highlighted}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_action:
        st.markdown('<div class="section-heading">Clinical Coding Recommendation</div>', unsafe_allow_html=True)
        st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

        rev_impact = gap.get("raf_delta", 0) * 12000
        st.markdown(f"""
        <div class="finding-panel">
            <div class="finding-header">
                <span class="finding-label">Suspected Uncoded Condition</span>
                <span class="finding-revenue">+${rev_impact:,.0f} / yr</span>
            </div>
            <div class="finding-body">
                <div class="finding-icd">{gap["suspected_icd10"]}</div>
                <div class="finding-desc">{gap["description"]} &nbsp; (HCC {gap["suspected_hcc"]})</div>
                <div class="finding-rationale">
                    <strong>Clinical Rationale:</strong> {gap["clinical_rationale"]}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        query_text = audit_result.get(
            "draft_clinician_query",
            f"Dr. {notes[0].author}, clinical documentation supports a diagnosis of diabetic neuropathy "
            f"(E11.40), which is not reflected in the active problem list. Please review and confirm "
            f"whether this diagnosis should be added to the patient record."
        )
        st.markdown(f"""
        <div class="query-panel">
            <div class="query-header">Auto-Generated Clinician Query</div>
            <div class="query-body">"{query_text}"</div>
            <div class="query-action">
                <button class="query-btn">Submit for Physician Review</button>
            </div>
        </div>
        """, unsafe_allow_html=True)

elif audit_result:
    st.markdown('<div class="audit-success">Audit complete. No coding gaps identified for this patient.</div>', unsafe_allow_html=True)

else:
    st.markdown('<div class="section-heading">Clinical Documentation</div>', unsafe_allow_html=True)
    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
    if notes:
        st.markdown(f"""
        <div class="card">
            <div class="note-header">
                {notes[0].note_type} &nbsp;&bull;&nbsp; {notes[0].authored_date} &nbsp;&bull;&nbsp; {notes[0].author}
            </div>
            <div class="note-body">{notes[0].content}</div>
        </div>
        """, unsafe_allow_html=True)
