# HCC Risk Navigator 🏥⚡

> **Hackathon:** Agents Assemble — The Healthcare AI Endgame (Prompt Opinion)
> **Category:** Superpower MCP Server (Option 1 — Interoperability)

A **FHIR-native Model Context Protocol (MCP) server** that acts as a Generative AI HCC Risk Adjustment auditing engine. Built for the Prompt Opinion platform to demonstrate the "Last Mile" of healthcare AI: not just summarizing data, but identifying **uncoded conditions in unstructured clinical notes to maximize Medicare Advantage RAF scores**.

---

## The Problem

Medicare Advantage plans rely on accurate HCC (Hierarchical Condition Category) coding to ensure appropriate care and funding (Risk Adjustment Factor, or RAF). Often, doctors document a condition in the unstructured text of a clinical note, but fail to add the specific ICD-10 code to the patient's problem list. This "HCC Gap" results in lower RAF scores, undervalued patient acuity, and lost revenue.

Manual chart audits take hours per patient.

**We automated it.**

---

## Architecture

```
Prompt Opinion Agent (cloud)
         │
         │  SHARP context (patient_id, FHIR token)
         ▼
    ngrok tunnel
         │
         ▼
┌──────────────────────────────────────┐
│  HCC Risk Navigator MCP Server       │
│  (FastAPI + MCP SSE transport)       │
│                                      │
│  GET  /mcp/sse    ← agent connects   │
│  POST /mcp/messages ← JSON-RPC calls │
│                                      │
│  Tools:                              │
│  └─ audit_hcc_opportunities(id)      │
│              │                       │
│              ▼                       │
│      hcc_engine.py (GPT-4o)          │
│              │                       │
│              ▼                       │
│     SQLite Mock EHR (FHIR R4)        │
└──────────────────────────────────────┘
```

---

## Quick Start

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/vjb/HCC-Risk-Navigator.git
cd FIRE

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -e ".[dev]"
playwright install chromium
```

### 2. Configure Environment

```bash
copy .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Seed the Mock EHR Database

```bash
python scripts/seed_db.py
```

This creates `data/mock_ehr.sqlite` with patient **Tamara Williams** (`tamara-williams-001`):
- Currently coded: `E11.9` (Type 2 Diabetes, HCC 19, RAF 0.104)
- Missing code (HCC Gap): `E11.40` (Diabetic Neuropathy, HCC 18, RAF 0.302)
- Clinical evidence in unstructured notes: "burning sensation in both feet ... Gabapentin"

### 4. Run Tests (TDD — Failing First, Then Green)

```bash
# All tests except UI (fast — no browser)
pytest tests/ -v --ignore=tests/test_ui.py

# MCP server + SSE transport tests specifically
pytest tests/test_mcp_server.py -v

# UI tests (requires Streamlit running)
pytest tests/test_ui.py -v
```

### 5. Start the MCP Server

```bash
python src/server.py
# OR
uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload
```

MCP SSE endpoints:
- `GET  http://localhost:8000/mcp/sse` — Prompt Opinion connects here
- `POST http://localhost:8000/mcp/messages` — JSON-RPC tool calls
- `GET  http://localhost:8000/health` — Health check
- `GET  http://localhost:8000/docs` — FastAPI Swagger UI

### 6. Start the Mock EHR Dashboard

```bash
streamlit run app.py
# Opens at http://localhost:8501
```

### 7. Tunnel via ngrok (for Prompt Opinion integration)

```bash
ngrok http 8000
# Copy the https://xxxx.ngrok.io URL
# In Prompt Opinion → Marketplace Studio → MCP Servers:
#   Transport: Streamable HTTP
#   URL: https://xxxx.ngrok.io/mcp/sse
```

---

## MCP Tools Reference

### `audit_hcc_opportunities(patient_id: str)`
Analyze a patient's FHIR chart for uncoded Hierarchical Condition Categories (HCCs). Returns projected RAF score improvements and clinical evidence quotes.
```json
{
  "gap_count": 1,
  "current_raf": 0.104,
  "projected_raf": 0.302,
  "raf_delta": 0.198,
  "gaps": [
    {
      "uncoded_icd10": "E11.40",
      "uncoded_description": "Type 2 diabetes mellitus with diabetic neuropathy",
      "hcc_category": 18,
      "raf_weight": 0.302,
      "clinical_evidence_quote": "worsening numbness and a burning sensation in both feet... Gabapentin 300mg (MEAT Compliance Data - Condition: Diabetic Peripheral Neuropathy, Symptoms: Worsening numbness, Treatments: Gabapentin 300mg)",
      "rationale": "Patient is actively treated for diabetic neuropathy with Gabapentin, but only generic diabetes E11.9 is coded.",
      "meat_criteria": {
        "condition": "Diabetic Peripheral Neuropathy",
        "symptoms": "Worsening numbness and a burning sensation in both feet",
        "treatments": "Gabapentin 300mg"
      }
    }
  ],
  "message": "Audit complete."
}
```

---

## Demo Script

See [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) for the complete 3-minute video script.

---

## Tech Stack

| Layer | Technology |
|---|---|
| MCP Server | `mcp` Python SDK (SSE transport) |
| API Framework | FastAPI + uvicorn |
| AI Reasoning | OpenAI GPT-4o |
| Database | SQLite via SQLAlchemy ORM |
| Data Standard | FHIR R4 (`fhir.resources`) |
| Synthetic Data | Faker |
| Dashboard | Streamlit |
| Testing | pytest + pytest-asyncio + Playwright |

---

## Project Structure

```
FIRE/
├── app.py                     # Streamlit Mock EHR Dashboard
├── src/
│   ├── database.py            # SQLAlchemy engine + session
│   ├── models.py              # ORM models (Patient, Medications, etc.)
│   ├── hcc_engine.py          # AI HCC Risk Adjustment gap detection core
│   └── server.py              # FastAPI + MCP SSE server
├── scripts/
│   └── seed_db.py             # Synthetic FHIR data seeder
├── tests/
│   ├── conftest.py            # Shared fixtures
│   ├── test_seed_db.py        # Data layer TDD tests
│   ├── test_hcc_auditor.py    # HCC gap engine TDD tests
│   ├── test_mcp_server.py     # MCP SSE transport tests
│   └── test_ui.py             # Playwright UI tests
└── docs/
    └── DEMO_SCRIPT.md         # 3-minute demo script
```
