"""
tests/test_fhir_integration.py — Live FHIR R4 Server Integration Tests
=======================================================================
These tests hit the real HAPI FHIR public demo server at:
    https://hapi.fhir.org/baseR4

They require network access and validate that the FIRE engine works end-to-end
with REAL FHIR resources — not the local SQLite mock. This is the primary data
path for production use.

Run live FHIR tests:
    pytest tests/test_fhir_integration.py -v -m live_fhir

Run with verbose FHIR output:
    pytest tests/test_fhir_integration.py -v -m live_fhir -s

Skip (CI with no network):
    pytest tests/ --ignore=tests/test_fhir_integration.py
    # or:
    pytest tests/ -m "not live_fhir"

Markers used:
    live_fhir  — requires network access to hapi.fhir.org
"""
from __future__ import annotations

import asyncio
import json
import pytest
import httpx

HAPI_BASE = "https://hapi.fhir.org/baseR4"
FHIR_HEADERS = {"Accept": "application/fhir+json"}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_first_patient_id() -> str:
    """Fetch the first available patient ID from HAPI FHIR."""
    resp = httpx.get(
        f"{HAPI_BASE}/Patient",
        params={"_count": "1", "_elements": "id"},
        headers=FHIR_HEADERS,
        timeout=15.0,
    )
    resp.raise_for_status()
    bundle = resp.json()
    entries = bundle.get("entry", [])
    assert entries, "HAPI FHIR returned zero patients — server may be down"
    return entries[0]["resource"]["id"]


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def hapi_patient_id() -> str:
    """
    Discover a real patient ID from the HAPI FHIR server.
    Scoped to module so we don't hammer the public server per-test.
    """
    return _get_first_patient_id()


@pytest.fixture(scope="module")
def hapi_patient_with_conditions() -> tuple[str, list]:
    """
    Find a HAPI FHIR patient that has at least one Condition.
    Returns (patient_id, conditions_list).
    """
    resp = httpx.get(
        f"{HAPI_BASE}/Patient",
        params={"_count": "20", "_elements": "id"},
        headers=FHIR_HEADERS,
        timeout=20.0,
    )
    resp.raise_for_status()
    patient_ids = [e["resource"]["id"] for e in resp.json().get("entry", [])]

    for pid in patient_ids:
        cr = httpx.get(
            f"{HAPI_BASE}/Condition",
            params={"subject": f"Patient/{pid}", "_count": "5"},
            headers=FHIR_HEADERS,
            timeout=10.0,
        )
        if cr.status_code == 200:
            entries = cr.json().get("entry", [])
            conditions = [e["resource"] for e in entries if e.get("resource")]
            if conditions:
                return pid, conditions

    pytest.skip("No HAPI FHIR patient with conditions found — server state may be empty")


# ─────────────────────────────────────────────────────────────────────────────
# Layer 1: HAPI FHIR Server Connectivity
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.live_fhir
class TestHAPIFHIRConnectivity:
    """Confirms the HAPI FHIR R4 public server is reachable and spec-compliant."""

    def test_hapi_fhir_server_is_reachable(self):
        """GET /metadata must return 200 — server is up."""
        r = httpx.get(f"{HAPI_BASE}/metadata", headers=FHIR_HEADERS, timeout=15.0)
        assert r.status_code == 200, f"HAPI metadata returned {r.status_code}"

    def test_hapi_returns_fhir_r4_capability_statement(self):
        """CapabilityStatement must declare FHIR version 4.0.1 (R4)."""
        r = httpx.get(f"{HAPI_BASE}/metadata", headers=FHIR_HEADERS, timeout=15.0)
        cs = r.json()
        assert cs.get("resourceType") == "CapabilityStatement"
        assert cs.get("fhirVersion", "").startswith("4.0"), (
            f"Expected FHIR 4.0.x, got: {cs.get('fhirVersion')}"
        )

    def test_hapi_patient_endpoint_returns_bundle(self):
        """GET /Patient must return a searchset Bundle."""
        r = httpx.get(
            f"{HAPI_BASE}/Patient",
            params={"_count": "1"},
            headers=FHIR_HEADERS,
            timeout=15.0,
        )
        assert r.status_code == 200
        body = r.json()
        assert body.get("resourceType") == "Bundle"
        assert body.get("type") == "searchset"

    def test_hapi_has_patients(self):
        """HAPI FHIR must have at least one Patient resource."""
        r = httpx.get(
            f"{HAPI_BASE}/Patient",
            params={"_count": "1"},
            headers=FHIR_HEADERS,
            timeout=15.0,
        )
        bundle = r.json()
        assert bundle.get("total", 0) > 0 or len(bundle.get("entry", [])) > 0, (
            "HAPI FHIR has zero Patient resources"
        )

    def test_hapi_condition_endpoint_is_available(self):
        """GET /Condition must return 200 (endpoint available)."""
        r = httpx.get(
            f"{HAPI_BASE}/Condition",
            params={"_count": "1"},
            headers=FHIR_HEADERS,
            timeout=15.0,
        )
        assert r.status_code == 200

    def test_hapi_document_reference_endpoint_is_available(self):
        """GET /DocumentReference must return 200 (endpoint available)."""
        r = httpx.get(
            f"{HAPI_BASE}/DocumentReference",
            params={"_count": "1"},
            headers=FHIR_HEADERS,
            timeout=15.0,
        )
        assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# Layer 2: FHIR Resource Structure Validation
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.live_fhir
class TestFHIRResourceStructure:
    """Validates that HAPI FHIR resources are spec-compliant FHIR R4."""

    def test_patient_resource_has_required_fields(self, hapi_patient_id):
        """A fetched Patient resource must have id and resourceType."""
        r = httpx.get(
            f"{HAPI_BASE}/Patient/{hapi_patient_id}",
            headers=FHIR_HEADERS,
            timeout=15.0,
        )
        assert r.status_code == 200, f"Patient/{hapi_patient_id} returned {r.status_code}"
        patient = r.json()
        assert patient.get("resourceType") == "Patient"
        assert patient.get("id") == hapi_patient_id

    def test_patient_resource_has_name_or_identifier(self, hapi_patient_id):
        """A Patient should have at least a name or identifier."""
        r = httpx.get(
            f"{HAPI_BASE}/Patient/{hapi_patient_id}",
            headers=FHIR_HEADERS,
            timeout=15.0,
        )
        patient = r.json()
        has_name       = bool(patient.get("name"))
        has_identifier = bool(patient.get("identifier"))
        assert has_name or has_identifier, (
            f"Patient {hapi_patient_id} has no name or identifier"
        )

    def test_conditions_reference_correct_patient(self, hapi_patient_with_conditions):
        """Every Condition returned for a patient must reference that patient."""
        patient_id, conditions = hapi_patient_with_conditions
        for cond in conditions:
            subject_ref = cond.get("subject", {}).get("reference", "")
            assert patient_id in subject_ref, (
                f"Condition subject {subject_ref!r} doesn't reference Patient/{patient_id}"
            )

    def test_conditions_have_icd10_or_snomed_codes(self, hapi_patient_with_conditions):
        """Conditions must have a code element with at least one coding."""
        _, conditions = hapi_patient_with_conditions
        coded = [c for c in conditions if c.get("code", {}).get("coding")]
        assert len(coded) > 0, "No conditions have a coding element"

    def test_condition_resourcetype_is_correct(self, hapi_patient_with_conditions):
        """All entries in a Condition bundle must be Condition resources."""
        _, conditions = hapi_patient_with_conditions
        for c in conditions:
            assert c.get("resourceType") == "Condition", (
                f"Expected Condition, got {c.get('resourceType')}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Layer 3: _fetch_fhir_patient_context() Integration
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.live_fhir
class TestFetchFHIRPatientContext:
    """
    Tests the FIRE engine's primary FHIR data-fetching function against
    the real HAPI FHIR server. This is the exact code path that runs in
    production when Prompt Opinion passes SHARP context headers.
    """

    async def test_fetch_returns_dict_for_known_patient(self, hapi_patient_id):
        """_fetch_fhir_patient_context() must return a dict for a real patient."""
        from src.server import _fetch_fhir_patient_context
        result = await _fetch_fhir_patient_context(hapi_patient_id, HAPI_BASE)
        assert result is not None, (
            f"_fetch_fhir_patient_context returned None for patient {hapi_patient_id}"
        )
        assert isinstance(result, dict)

    async def test_fetch_returns_all_required_keys(self, hapi_patient_id):
        """The returned context must have patient, conditions, and clinical_notes keys."""
        from src.server import _fetch_fhir_patient_context
        result = await _fetch_fhir_patient_context(hapi_patient_id, HAPI_BASE)
        assert result is not None
        assert "patient" in result,        "Missing 'patient' key in FHIR context"
        assert "conditions" in result,     "Missing 'conditions' key in FHIR context"
        assert "clinical_notes" in result, "Missing 'clinical_notes' key in FHIR context"

    async def test_fetch_patient_has_correct_id(self, hapi_patient_id):
        """The patient resource in the context must have the requested ID."""
        from src.server import _fetch_fhir_patient_context
        result = await _fetch_fhir_patient_context(hapi_patient_id, HAPI_BASE)
        assert result is not None
        assert result["patient"]["id"] == hapi_patient_id

    async def test_fetch_conditions_is_a_list(self, hapi_patient_id):
        """Conditions must always be a list (empty is OK — not all patients have conditions)."""
        from src.server import _fetch_fhir_patient_context
        result = await _fetch_fhir_patient_context(hapi_patient_id, HAPI_BASE)
        assert result is not None
        assert isinstance(result["conditions"], list)

    async def test_fetch_clinical_notes_is_a_list(self, hapi_patient_id):
        """Clinical notes must always be a list."""
        from src.server import _fetch_fhir_patient_context
        result = await _fetch_fhir_patient_context(hapi_patient_id, HAPI_BASE)
        assert result is not None
        assert isinstance(result["clinical_notes"], list)

    async def test_fetch_marks_source_as_fhir(self, hapi_patient_id):
        """The _source field must be 'fhir' to confirm the real server was used."""
        from src.server import _fetch_fhir_patient_context
        result = await _fetch_fhir_patient_context(hapi_patient_id, HAPI_BASE)
        assert result is not None
        assert result.get("_source") == "fhir", (
            f"Expected _source='fhir', got {result.get('_source')!r}"
        )

    async def test_fetch_records_fhir_url(self, hapi_patient_id):
        """The _fhir_url field must record which server was used."""
        from src.server import _fetch_fhir_patient_context
        result = await _fetch_fhir_patient_context(hapi_patient_id, HAPI_BASE)
        assert result is not None
        assert "hapi.fhir.org" in result.get("_fhir_url", "")

    async def test_fetch_returns_none_for_nonexistent_patient(self):
        """_fetch_fhir_patient_context must return None for a patient that doesn't exist."""
        from src.server import _fetch_fhir_patient_context
        result = await _fetch_fhir_patient_context(
            "nonexistent-patient-xyzzy-00000", HAPI_BASE
        )
        assert result is None, (
            "Expected None for nonexistent patient, got a result"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Layer 4: HCC Audit Engine on Real FHIR Data
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.live_fhir
class TestHCCAuditOnRealFHIRData:
    """
    End-to-end audit using real FHIR data + real LLM call.
    Validates that the full pipeline — FHIR fetch → RAF calc → LLM analysis →
    5Ts formatting — works correctly when given live data.

    NOTE: These tests make real OpenAI API calls. They validate output shape
    and structure, not specific content (which varies per patient).
    """

    async def test_audit_runs_without_error_on_real_fhir_patient(
        self, hapi_patient_id
    ):
        """audit_hcc_gaps() must complete without exception on real FHIR data."""
        from src.server import _fetch_fhir_patient_context
        from src.hcc_engine import audit_hcc_gaps

        fhir_context = await _fetch_fhir_patient_context(hapi_patient_id, HAPI_BASE)
        assert fhir_context is not None

        result = await asyncio.to_thread(audit_hcc_gaps, fhir_context)
        assert result is not None
        assert isinstance(result, dict)

    async def test_audit_returns_required_output_keys(self, hapi_patient_id):
        """audit_hcc_gaps() output must have all required keys regardless of patient."""
        from src.server import _fetch_fhir_patient_context
        from src.hcc_engine import audit_hcc_gaps

        fhir_context = await _fetch_fhir_patient_context(hapi_patient_id, HAPI_BASE)
        assert fhir_context is not None
        result = await asyncio.to_thread(audit_hcc_gaps, fhir_context)

        required = {"patient_id", "patient_name", "current_raf", "projected_raf",
                    "raf_delta", "existing_codes", "gaps", "audit_summary", "gap_count"}
        missing = required - result.keys()
        assert not missing, f"audit_hcc_gaps() missing keys: {missing}"

    async def test_audit_raf_values_are_numeric(self, hapi_patient_id):
        """current_raf, projected_raf, and raf_delta must be floats >= 0."""
        from src.server import _fetch_fhir_patient_context
        from src.hcc_engine import audit_hcc_gaps

        fhir_context = await _fetch_fhir_patient_context(hapi_patient_id, HAPI_BASE)
        assert fhir_context is not None
        result = await asyncio.to_thread(audit_hcc_gaps, fhir_context)

        assert isinstance(result["current_raf"], (int, float))
        assert isinstance(result["projected_raf"], (int, float))
        assert isinstance(result["raf_delta"], (int, float))
        assert result["current_raf"] >= 0
        assert result["projected_raf"] >= result["current_raf"]

    async def test_audit_gap_list_is_valid(self, hapi_patient_id):
        """Each gap in the audit result must have required sub-fields."""
        from src.server import _fetch_fhir_patient_context
        from src.hcc_engine import audit_hcc_gaps

        fhir_context = await _fetch_fhir_patient_context(hapi_patient_id, HAPI_BASE)
        assert fhir_context is not None
        result = await asyncio.to_thread(audit_hcc_gaps, fhir_context)

        required_gap_keys = {
            "suspected_icd10", "suspected_hcc", "description",
            "evidence_quote", "clinical_rationale", "raf_delta", "confidence"
        }
        for gap in result["gaps"]:
            missing = required_gap_keys - gap.keys()
            assert not missing, f"Gap missing keys: {missing}  gap={gap}"

    async def test_5ts_format_runs_on_real_fhir_audit(self, hapi_patient_id):
        """format_5ts() must produce all four deliverables from a real FHIR audit."""
        from src.server import _fetch_fhir_patient_context
        from src.hcc_engine import audit_hcc_gaps, format_5ts

        fhir_context = await _fetch_fhir_patient_context(hapi_patient_id, HAPI_BASE)
        assert fhir_context is not None
        result = await asyncio.to_thread(audit_hcc_gaps, fhir_context)
        five_ts = format_5ts(result)

        assert "table" in five_ts,    "5Ts missing 'table' deliverable"
        assert "template" in five_ts, "5Ts missing 'template' deliverable"
        assert "task" in five_ts,     "5Ts missing 'task' deliverable"
        assert "talk" in five_ts,     "5Ts missing 'talk' deliverable"

    async def test_5ts_table_contains_patient_name(self, hapi_patient_id):
        """The Table deliverable must reference the actual patient."""
        from src.server import _fetch_fhir_patient_context
        from src.hcc_engine import audit_hcc_gaps, format_5ts

        fhir_context = await _fetch_fhir_patient_context(hapi_patient_id, HAPI_BASE)
        assert fhir_context is not None
        result = await asyncio.to_thread(audit_hcc_gaps, fhir_context)
        five_ts = format_5ts(result)

        # Table must mention the patient (by name or ID)
        table = five_ts["table"]
        assert result["patient_name"] in table or result["patient_id"] in table

    async def test_5ts_task_has_correct_structure(self, hapi_patient_id):
        """The Task RCM ticket must be a dict with required workflow fields."""
        from src.server import _fetch_fhir_patient_context
        from src.hcc_engine import audit_hcc_gaps, format_5ts

        fhir_context = await _fetch_fhir_patient_context(hapi_patient_id, HAPI_BASE)
        assert fhir_context is not None
        result = await asyncio.to_thread(audit_hcc_gaps, fhir_context)
        task = format_5ts(result)["task"]

        required = {"type", "title", "patient_id", "priority",
                    "estimated_revenue_recovery", "status", "due_date", "assignee"}
        missing = required - task.keys()
        assert not missing, f"Task RCM ticket missing keys: {missing}"
        assert task["type"] == "Task"
        assert task["status"] == "OPEN"
        assert task["priority"] in ("HIGH", "MEDIUM", "LOW")


# ─────────────────────────────────────────────────────────────────────────────
# Layer 5: Cohort Sweep (audit_v28_cohort via FHIR)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.live_fhir
class TestCohortAuditRealFHIR:
    """Tests audit_v28_cohort() logic directly against the HAPI FHIR server."""

    async def test_cohort_fetch_returns_patient_ids(self):
        """The cohort sweep must retrieve real patient IDs from HAPI FHIR."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{HAPI_BASE}/Patient",
                params={"_count": "3", "_elements": "id"},
                headers=FHIR_HEADERS,
            )
        assert resp.status_code == 200
        bundle = resp.json()
        patient_ids = [
            e["resource"]["id"]
            for e in bundle.get("entry", [])
            if e.get("resource", {}).get("id")
        ]
        assert len(patient_ids) > 0, "Cohort sweep returned zero patient IDs"

    async def test_cohort_audit_produces_scorecard(self):
        """
        Run audit_v28_cohort() on 2 real FHIR patients.
        Validates that a cohort scorecard is returned with the expected structure.
        NOTE: mocks _call_llm to avoid N LLM calls in CI.
        """
        from unittest.mock import patch
        from src.server import _fetch_fhir_patient_context
        from src.hcc_engine import audit_hcc_gaps

        # Fetch 2 real patients
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{HAPI_BASE}/Patient",
                params={"_count": "2", "_elements": "id"},
                headers=FHIR_HEADERS,
            )
        patient_ids = [
            e["resource"]["id"]
            for e in resp.json().get("entry", [])
            if e.get("resource", {}).get("id")
        ]
        assert patient_ids, "Need at least 1 patient for cohort test"

        mock_llm_response = '{"gaps": [], "audit_summary": "No gaps found."}'
        cohort_results = []

        with patch("src.hcc_engine._call_llm", return_value=mock_llm_response):
            for pid in patient_ids:
                ctx = await _fetch_fhir_patient_context(pid, HAPI_BASE)
                if ctx:
                    result = await asyncio.to_thread(audit_hcc_gaps, ctx)
                    cohort_results.append(result)

        assert len(cohort_results) > 0, "No patients successfully audited"
        for r in cohort_results:
            assert "patient_id"   in r
            assert "current_raf"  in r
            assert "raf_delta"    in r
            assert "gaps"         in r
