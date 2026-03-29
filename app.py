"""
app.py — Auto-Auth Pre-Cog Engine: Mock EHR Dashboard
=======================================================
Streamlit dashboard displaying patient Tamara Chen's FHIR timeline.
Used as the visual anchor for the 3-minute hackathon demo.

Tabs:
  1. Patient Overview — demographics, banner card
  2. FHIR Timeline    — Medications table + A1C chart
  3. Clinical Notes   — DocumentReference viewer with GI note highlighted
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime

import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Page Config (must be the very first Streamlit command)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Auto-Auth Pre-Cog — Mock EHR",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Environment & DB Setup
# ─────────────────────────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))
from src.database import get_session, init_db
from src.models import ClinicalNote, MedicationRequest, Observation, Patient

init_db()

# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS — Clinical Dark Theme
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

.main { background: #0a0f1e; }
.stApp { background: linear-gradient(135deg, #0a0f1e 0%, #0d1535 50%, #0a1628 100%); }

/* ── Hide default Streamlit chrome ── */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }

/* ── Patient Banner ── */
.patient-banner {
    background: linear-gradient(135deg, #1a2744 0%, #0f3460 50%, #16213e 100%);
    border: 1px solid rgba(99, 179, 237, 0.3);
    border-radius: 16px;
    padding: 24px 32px;
    margin-bottom: 24px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255,255,255,0.05);
    position: relative;
    overflow: hidden;
}
.patient-banner::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(99, 179, 237, 0.08) 0%, transparent 70%);
    border-radius: 50%;
}
.patient-name {
    font-size: 2rem;
    font-weight: 700;
    color: #e2e8f0;
    margin: 0 0 4px 0;
    letter-spacing: -0.02em;
}
.patient-meta {
    font-size: 0.9rem;
    color: #94a3b8;
    margin: 0;
}
.fhir-id-badge {
    display: inline-block;
    background: rgba(99, 179, 237, 0.15);
    border: 1px solid rgba(99, 179, 237, 0.4);
    color: #63b3ed;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-family: 'Courier New', monospace;
    margin-top: 8px;
}

/* ── Metric Cards ── */
.metric-card {
    background: rgba(22, 33, 62, 0.8);
    border: 1px solid rgba(99, 179, 237, 0.15);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    backdrop-filter: blur(10px);
    transition: all 0.2s ease;
}
.metric-card:hover {
    border-color: rgba(99, 179, 237, 0.4);
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(99, 179, 237, 0.1);
}
.metric-value {
    font-size: 2rem;
    font-weight: 700;
    color: #63b3ed;
    line-height: 1;
}
.metric-label {
    font-size: 0.8rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 6px;
}

/* ── Alert Cards ── */
.alert-warning {
    background: rgba(251, 191, 36, 0.08);
    border: 1px solid rgba(251, 191, 36, 0.4);
    border-left: 4px solid #f59e0b;
    border-radius: 8px;
    padding: 14px 18px;
    margin: 12px 0;
    color: #fcd34d;
}
.alert-danger {
    background: rgba(239, 68, 68, 0.08);
    border: 1px solid rgba(239, 68, 68, 0.4);
    border-left: 4px solid #ef4444;
    border-radius: 8px;
    padding: 14px 18px;
    margin: 12px 0;
    color: #fca5a5;
}
.alert-evidence {
    background: rgba(16, 185, 129, 0.08);
    border: 1px solid rgba(16, 185, 129, 0.4);
    border-left: 4px solid #10b981;
    border-radius: 8px;
    padding: 14px 18px;
    margin: 12px 0;
    color: #6ee7b7;
}

/* ── Section Headers ── */
.section-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: #e2e8f0;
    padding: 8px 0;
    border-bottom: 1px solid rgba(99, 179, 237, 0.2);
    margin-bottom: 16px;
}

/* ── Clinical Note Card ── */
.note-card {
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(71, 85, 105, 0.4);
    border-radius: 10px;
    padding: 20px;
    margin: 12px 0;
    font-family: 'Courier New', monospace;
    font-size: 0.82rem;
    line-height: 1.6;
    color: #cbd5e1;
    white-space: pre-wrap;
}
.note-card.highlighted {
    border-color: rgba(16, 185, 129, 0.5);
    background: rgba(16, 185, 129, 0.04);
    box-shadow: 0 0 20px rgba(16, 185, 129, 0.08);
}
.note-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}
.note-type-badge {
    display: inline-block;
    background: rgba(99, 179, 237, 0.15);
    border: 1px solid rgba(99, 179, 237, 0.3);
    color: #93c5fd;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.72rem;
    font-family: 'Inter', sans-serif;
    font-weight: 500;
}
.exception-badge {
    background: rgba(16, 185, 129, 0.2);
    border-color: rgba(16, 185, 129, 0.5);
    color: #6ee7b7;
}

/* ── Sidebar ── */
.css-1d391kg, [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
    border-right: 1px solid rgba(99, 179, 237, 0.1);
}

/* ── DataFrame styling ── */
.stDataFrame {
    border-radius: 8px;
    overflow: hidden;
}

/* ── Tab styling ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    background: rgba(30, 41, 59, 0.6);
    border: 1px solid rgba(99, 179, 237, 0.15);
    border-radius: 8px;
    color: #94a3b8;
    font-weight: 500;
    padding: 8px 20px;
}
.stTabs [aria-selected="true"] {
    background: rgba(99, 179, 237, 0.15) !important;
    border-color: rgba(99, 179, 237, 0.5) !important;
    color: #63b3ed !important;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Data Loading
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_patient_data(patient_fhir_id: str = "tamara-chen-001"):
    """Load all patient data from the Mock EHR SQLite database."""
    session = get_session()
    try:
        patient = session.query(Patient).filter_by(fhir_id=patient_fhir_id).first()
        if not patient:
            return None, [], [], []

        medications = session.query(MedicationRequest).filter_by(patient_id=patient.id).order_by(
            MedicationRequest.start_date
        ).all()
        observations = session.query(Observation).filter_by(patient_id=patient.id).order_by(
            Observation.effective_date
        ).all()
        notes = session.query(ClinicalNote).filter_by(patient_id=patient.id).order_by(
            ClinicalNote.authored_date
        ).all()

        # Convert to plain dicts to be safe with Streamlit caching
        patient_dict = {
            "fhir_id": patient.fhir_id,
            "name": patient.name,
            "dob": patient.dob,
            "gender": patient.gender,
        }
        meds_list = [
            {
                "Medication": m.medication_name,
                "Dosage": m.dosage or "—",
                "Start Date": m.start_date,
                "End Date": m.end_date or "Ongoing",
                "Status": m.status.title(),
                "Duration (days)": (
                    (date.fromisoformat(m.end_date) - date.fromisoformat(m.start_date)).days
                    if m.end_date else (date.today() - date.fromisoformat(m.start_date)).days
                ),
            }
            for m in medications
        ]
        obs_list = [
            {
                "Date": o.effective_date,
                "Test": o.display,
                "Value": o.value,
                "Unit": o.unit,
                "LOINC": o.loinc_code,
            }
            for o in observations
        ]
        notes_list = [
            {
                "type": n.note_type,
                "date": n.authored_date,
                "author": n.author or "Unknown",
                "content": n.content,
            }
            for n in notes
        ]
        return patient_dict, meds_list, obs_list, notes_list
    finally:
        session.close()


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — Patient Selector & System Info
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 12px 0 20px;">
        <div style="font-size:2.5rem;">🏥</div>
        <div style="font-size:1rem; font-weight:700; color:#e2e8f0; margin-top:4px;">Auto-Auth</div>
        <div style="font-size:0.75rem; color:#94a3b8;">Pre-Cog Engine</div>
        <div style="font-size:0.65rem; color:#475569; margin-top:4px; letter-spacing:0.1em;">MOCK EHR DASHBOARD</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**🔗 Active Patient**")
    selected_patient_id = st.selectbox(
        "Patient FHIR ID",
        ["tamara-chen-001"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("**⚕️ MCP Server**")
    server_port = os.getenv("MCP_SERVER_PORT", "8000")
    st.markdown(f"""
    <div style="background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3); border-radius:8px; padding:10px 12px;">
        <div style="color:#6ee7b7; font-size:0.75rem; font-weight:600;">● RUNNING</div>
        <div style="color:#94a3b8; font-size:0.72rem; margin-top:4px;">localhost:{server_port}/mcp</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**🛠️ MCP Tools**")
    for tool in ["get_fhir_context", "hunt_clinical_evidence", "generate_pa_justification"]:
        st.markdown(f"<div style='color:#94a3b8; font-size:0.78rem; padding:3px 0;'>→ {tool}</div>", unsafe_allow_html=True)

    st.markdown("---")
    if st.button("🌱 Re-seed Database", use_container_width=True):
        with st.spinner("Seeding..."):
            import subprocess
            result = subprocess.run(["python", "scripts/seed_db.py"], capture_output=True, text=True)
            if result.returncode == 0:
                st.success("Database re-seeded!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(f"Seeding failed: {result.stderr}")


# ─────────────────────────────────────────────────────────────────────────────
# Main Content
# ─────────────────────────────────────────────────────────────────────────────

patient, medications, observations, notes = load_patient_data(selected_patient_id)

if not patient:
    st.error("❌ No patient data found. Run `python scripts/seed_db.py` first.")
    st.stop()

# ── Patient Banner ────────────────────────────────────────────────────────────
dob = date.fromisoformat(patient["dob"])
age = (date.today() - dob).days // 365
gender_icon = "♀" if patient["gender"] == "female" else "♂"

st.markdown(f"""
<div class="patient-banner">
    <p class="patient-name">{gender_icon} {patient['name']}</p>
    <p class="patient-meta">
        DOB: {patient['dob']} &nbsp;·&nbsp; 
        Age: {age} years &nbsp;·&nbsp; 
        Gender: {patient['gender'].title()} &nbsp;·&nbsp;
        Diagnosis: Type 2 Diabetes Mellitus
    </p>
    <span class="fhir-id-badge">FHIR: {patient['fhir_id']}</span>
</div>
""", unsafe_allow_html=True)

# ── PA Status Alert ───────────────────────────────────────────────────────────
st.markdown("""
<div class="alert-warning">
    ⚠️ <strong>Prior Authorization Alert</strong> — Ozempic (semaglutide) PA request pending. 
    Step-therapy deficient: 61 days completed of 180 days required. Clinical exception evidence available.
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🧬 Patient Overview", "📊 FHIR Timeline", "📋 Clinical Notes"])


# ─── Tab 1: Patient Overview ──────────────────────────────────────────────────
with tab1:
    col1, col2, col3, col4 = st.columns(4)

    metformin_days = medications[0]["Duration (days)"] if medications else 0
    latest_a1c = observations[-1]["Value"] if observations else 0
    num_notes = len(notes)
    num_meds = len(medications)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{metformin_days}d</div>
            <div class="metric-label">Metformin Duration</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        a1c_color = "#ef4444" if latest_a1c > 8.0 else "#f59e0b" if latest_a1c > 7.0 else "#10b981"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color:{a1c_color}">{latest_a1c}%</div>
            <div class="metric-label">Latest A1C</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{num_meds}</div>
            <div class="metric-label">Medications</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color:#10b981">{num_notes}</div>
            <div class="metric-label">Clinical Notes</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.markdown('<div class="section-header">📋 Demographics</div>', unsafe_allow_html=True)
        fields = {
            "Full Name": patient["name"],
            "Date of Birth": patient["dob"],
            "Age": f"{age} years",
            "Gender": patient["gender"].title(),
            "FHIR Patient ID": patient["fhir_id"],
            "Primary Diagnosis": "Type 2 Diabetes Mellitus (E11.9)",
            "Requested Medication": "Ozempic (semaglutide 0.5mg weekly SC)",
            "Ordering Physician": "Dr. Sarah Morrison, MD",
            "Insurance": "Aetna — Commercial PPO",
        }
        for k, v in fields.items():
            col_k, col_v = st.columns([1, 1.5])
            col_k.markdown(f"<span style='color:#64748b; font-size:0.82rem;'>{k}</span>", unsafe_allow_html=True)
            col_v.markdown(f"<span style='color:#e2e8f0; font-size:0.85rem; font-weight:500;'>{v}</span>", unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="section-header">🔍 PA Case Summary</div>', unsafe_allow_html=True)

        st.markdown("""
        <div class="alert-danger">
            ❌ <strong>Step Therapy: NOT MET</strong><br>
            Metformin trial: 61 days completed<br>
            Aetna requirement: 180 days (6 months)
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="alert-evidence">
            ✅ <strong>Clinical Exception: FOUND</strong><br>
            Progress note documents <strong>severe GI intolerance</strong> to Metformin.<br>
            Medication discontinued due to gastrointestinal adverse effects.
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="background:rgba(99,179,237,0.08); border:1px solid rgba(99,179,237,0.25); border-radius:8px; padding:14px; margin-top:12px;">
            <div style="color:#93c5fd; font-size:0.85rem; font-weight:600;">🤖 AI Recommendation</div>
            <div style="color:#cbd5e1; font-size:0.82rem; margin-top:6px; line-height:1.5;">
            Step-therapy deficiency qualifies for clinical exception bypass under Aetna policy §4.2(b). 
            PA Exception Request drafted and ready for submission.
            </div>
        </div>
        """, unsafe_allow_html=True)


# ─── Tab 2: FHIR Timeline ────────────────────────────────────────────────────
with tab2:
    col_meds, col_obs = st.columns([1, 1])

    with col_meds:
        st.markdown('<div class="section-header">💊 Medication History</div>', unsafe_allow_html=True)
        if medications:
            import pandas as pd
            meds_df = pd.DataFrame(medications)
            st.dataframe(
                meds_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Medication": st.column_config.TextColumn("Medication", width="large"),
                    "Duration (days)": st.column_config.NumberColumn("Duration (days)", format="%d days"),
                    "Status": st.column_config.TextColumn("Status"),
                },
            )

            duration = medications[0]["Duration (days)"] if medications else 0
            required = 180
            pct = min(duration / required, 1.0)
            st.markdown(f"""
            <div style="margin-top:16px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                    <span style="color:#94a3b8; font-size:0.8rem;">Step-Therapy Progress</span>
                    <span style="color:#f59e0b; font-size:0.8rem; font-weight:600;">{duration}d / {required}d required</span>
                </div>
                <div style="background:rgba(30,41,59,0.8); border-radius:6px; height:12px; overflow:hidden;">
                    <div style="width:{pct*100:.1f}%; height:100%; background:linear-gradient(90deg, #f59e0b, #ef4444); border-radius:6px; transition:width 0.5s;"></div>
                </div>
                <div style="text-align:right; margin-top:4px; color:#ef4444; font-size:0.75rem;">⚠️ {100-pct*100:.0f}% remaining — step therapy incomplete</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No medication records found.")

    with col_obs:
        st.markdown('<div class="section-header">🧪 Lab Results (A1C Trend)</div>', unsafe_allow_html=True)
        if observations:
            import pandas as pd
            obs_df = pd.DataFrame(observations)
            a1c_df = obs_df[obs_df["LOINC"] == "4548-4"].copy()

            if not a1c_df.empty:
                a1c_df["Date"] = pd.to_datetime(a1c_df["Date"])
                a1c_df = a1c_df.sort_values("Date")
                a1c_df["A1C (%)"] = a1c_df["Value"]

                # Chart
                st.line_chart(
                    a1c_df.set_index("Date")[["A1C (%)"]],
                    color="#ef4444",
                    height=220,
                )

                # Reference lines annotation
                st.markdown("""
                <div style="display:flex; gap:16px; margin-top:4px; font-size:0.75rem; color:#64748b;">
                    <span>📍 Normal: &lt;5.7%</span>
                    <span>📍 Pre-diabetic: 5.7–6.4%</span>
                    <span style="color:#ef4444;">📍 Diabetic: ≥6.5%</span>
                </div>
                """, unsafe_allow_html=True)

            st.dataframe(
                obs_df[["Date", "Test", "Value", "Unit"]].rename(columns={"Value": "Result"}),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No lab results found.")


# ─── Tab 3: Clinical Notes ────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-header">📋 DocumentReference Records</div>', unsafe_allow_html=True)

    EXCEPTION_KEYWORDS_DISPLAY = [
        "GI intolerance", "gastrointestinal", "discontinued", "adverse effect",
        "intolerance", "unable to tolerate",
    ]

    for note in notes:
        content_lower = note["content"].lower()
        is_exception_evidence = any(kw.lower() in content_lower for kw in EXCEPTION_KEYWORDS_DISPLAY)

        highlight_class = "highlighted" if is_exception_evidence else ""
        exception_badge = ""
        if is_exception_evidence:
            exception_badge = '<span class="note-type-badge exception-badge">✅ Exception Evidence</span>'

        st.markdown(f"""
        <div class="note-card {highlight_class}">
            <div class="note-header">
                <div>
                    <span class="note-type-badge">{note['type']}</span>
                    {exception_badge}
                </div>
                <span style="color:#64748b; font-size:0.75rem;">{note['date']} · {note['author']}</span>
            </div>
            <div style="border-top:1px solid rgba(71,85,105,0.3); padding-top:12px; margin-top:4px;">
{note['content']}
            </div>
        </div>
        """, unsafe_allow_html=True)

        if is_exception_evidence:
            st.markdown("""
            <div class="alert-evidence" style="margin: -4px 0 16px 0; font-size:0.82rem;">
                🔬 <strong>MCP Tool: hunt_clinical_evidence</strong> — This note contains qualifying 
                exception evidence (GI intolerance + discontinuation). The AI Prior Auth agent 
                will cite this note in the PA Exception Request.
            </div>
            """, unsafe_allow_html=True)
