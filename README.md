# Auto-Auth Pre-Cog Engine 🏥⚡

> **Hackathon:** Agents Assemble — The Healthcare AI Endgame (Prompt Opinion)
> **Category:** Superpower MCP Server (Option 1 — Interoperability)

A **FHIR-native Model Context Protocol (MCP) server** that acts as a Generative AI Prior Authorization reasoning engine. Built for the Prompt Opinion platform to demonstrate the "Last Mile" of healthcare AI: not just summarizing data, but producing a **final, submittable PA Exception Request**.

---

## The Problem

Ozempic prior authorizations are denied **80%+ of the time** on first submission. Most denials are step-therapy failures — the insurance company requires proof that cheaper drugs (like Metformin) were tried first. But what if the patient *couldn't tolerate* that drug? A human has to manually hunt through clinical notes, match it to policy language, and draft a legal-quality exception letter. This takes hours.

**We automated it in seconds.**

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
│   Auto-Auth Pre-Cog MCP Server       │
│   (FastAPI + MCP SSE transport)      │
│                                      │
│  GET  /mcp/sse    ← agent connects   │
│  POST /mcp/messages ← JSON-RPC calls │
│                                      │
│  Tools:                              │
│  ┌─ get_fhir_context(patient_id)     │
│  ├─ hunt_clinical_evidence(id, kw)   │
│  └─ generate_pa_justification(...)   │
│              │                       │
│              ▼                       │
│       pa_engine.py (GPT-4o-mini)     │
│              │                       │
│              ▼                       │
│     SQLite Mock EHR (FHIR R4)        │
└──────────────────────────────────────┘
```

---

## Quick Start

### 1. Clone & Set Up Environment

```bash
git clone <repo>
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

This creates `data/mock_ehr.sqlite` with patient **Tamara Chen**:
- 2 months of Metformin 500mg (completed — step therapy incomplete)
- 3 A1C lab results (7.8% → 8.1% → 8.6% — rising, poorly controlled)
- 1 clinical progress note documenting **severe GI intolerance** + Metformin discontinuation

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

### `get_fhir_context(patient_id: str)`
Returns the full FHIR R4 context for a patient:
```json
{
  "patient": { "name": "Tamara Chen", "dob": "1978-04-15", ... },
  "medications": [{ "medication_name": "Metformin", "start_date": "...", "end_date": "...", "status": "completed" }],
  "observations": [{ "loinc_code": "4548-4", "value": 8.6, "unit": "%" }],
  "clinical_notes": [{ "content": "...severe GI intolerance...", "authored_date": "..." }]
}
```

### `hunt_clinical_evidence(patient_id: str, condition_keyword: str)`
Searches clinical notes for exception evidence:
```json
{
  "patient_id": "tamara-chen-001",
  "keyword": "GI intolerance",
  "matching_notes": [{ "note_type": "Progress Note", "content": "..." }]
}
```

### `generate_pa_justification(patient_id: str, target_medication: str, policy_text: str)`
Full AI reasoning pipeline → structured PA analysis:
```json
{
  "step_therapy_met": false,
  "therapy_duration_days": 61,
  "required_duration_days": 180,
  "exception_found": true,
  "exception_evidence": "Clinical note documents severe GI intolerance...",
  "pa_letter": "PRIOR AUTHORIZATION EXCEPTION REQUEST\n\nTo: Aetna..."
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
| AI Reasoning | OpenAI GPT-4o-mini |
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
│   ├── pa_engine.py           # AI PA reasoning core
│   └── server.py              # FastAPI + MCP SSE server
├── scripts/
│   └── seed_db.py             # Synthetic FHIR data seeder
├── tests/
│   ├── conftest.py            # Shared fixtures
│   ├── test_seed_db.py        # Data layer TDD tests
│   ├── test_pa_reasoning.py   # PA engine TDD tests
│   ├── test_mcp_server.py     # MCP SSE transport tests
│   └── test_ui.py             # Playwright UI tests
└── docs/
    └── DEMO_SCRIPT.md         # 3-minute demo script
```
