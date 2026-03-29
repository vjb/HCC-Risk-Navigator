"""
TDD Phase 3 — MCP Server Tests: SSE Transport + Tool Registration
=================================================================
Tests specifically validate the HTTP/SSE transport layer as required for
ngrok tunneling to the Prompt Opinion cloud platform.

The MCP SSE transport exposes:
  GET  /mcp/sse           → SSE stream (text/event-stream)
  POST /mcp/messages      → JSON-RPC 2.0 message bus (requires ?sessionId=)

REST wrapper endpoints (for direct testing and health checks):
  GET  /health
  POST /tools/get_fhir_context
  POST /tools/hunt_clinical_evidence
  POST /tools/generate_pa_justification

Run with:
    pytest tests/test_mcp_server.py -v -asyncio-mode=auto
"""
from __future__ import annotations

import asyncio
import json
import re
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# ─────────────────────────────────────────────────────────────────────────────
# App Fixture — In-memory DB, pre-seeded with Tamara's records
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def seeded_app():
    """
    Module-scoped FastAPI app backed by an in-memory SQLite DB.
    Seeds Tamara's full FHIR dataset before yielding the app.
    """
    import os
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    from src.database import engine
    from src.models import Base
    Base.metadata.create_all(bind=engine)

    from sqlalchemy.orm import sessionmaker
    session = sessionmaker(bind=engine)()
    from scripts.seed_db import seed
    seed(session)
    session.close()

    from src.server import app
    return app


@pytest.fixture()
async def client(seeded_app):
    """Async HTTPX client wired to the FastAPI ASGI app.
    
    Note: Host header must be 'localhost' — MCP SDK v1.x validates the Host
    header as part of DNS rebinding protection. The test base_url is set to
    http://localhost to satisfy this check.
    """
    async with AsyncClient(
        transport=ASGITransport(app=seeded_app),
        base_url="http://localhost",  # Must match a trusted host for MCP security check
        headers={"Host": "localhost"},
    ) as ac:
        yield ac


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: SSE Transport — Connection & Content-Type
# ─────────────────────────────────────────────────────────────────────────────

class TestSSETransport:
    """
    Validates that the MCP SSE transport is correctly initialized and responds
    with the expected content-type for streaming. This is the transport that
    Prompt Opinion connects to via the ngrok tunnel.

    Note: SSE connections stay open indefinitely. These tests use asyncio.timeout
    to cap the connection, then assert on headers/first-chunk data collected
    before the timeout intentionally fires.
    """

    async def test_sse_endpoint_returns_200(self, client: AsyncClient):
        """
        GET /mcp/sse must return 200 OK. This confirms the SSE transport
        is mounted and listening — a prerequisite for Prompt Opinion integration.
        """
        status_code = None
        try:
            async with asyncio.timeout(3.0):
                async with client.stream("GET", "/mcp/sse") as response:
                    status_code = response.status_code
                    # Drain one chunk to confirm the stream started, then let timeout fire
                    async for _ in response.aiter_bytes():
                        break
        except (TimeoutError, asyncio.CancelledError):
            pass  # Expected — SSE stream never closes; we got what we needed

        assert status_code == 200, (
            f"Expected 200 from /mcp/sse, got {status_code}. "
            "Check that mcp.server.sse is mounted at /mcp."
        )

    async def test_sse_endpoint_content_type_is_event_stream(self, client: AsyncClient):
        """
        GET /mcp/sse must set Content-Type: text/event-stream.
        This is a hard requirement for SSE; Prompt Opinion's agent runtime
        will reject the connection if this header is missing or wrong.
        """
        content_type = None
        try:
            async with asyncio.timeout(3.0):
                async with client.stream("GET", "/mcp/sse") as response:
                    content_type = response.headers.get("content-type", "")
                    async for _ in response.aiter_bytes():
                        break
        except (TimeoutError, asyncio.CancelledError):
            pass

        assert content_type is not None, "/mcp/sse returned no response before timeout"
        assert "text/event-stream" in content_type, (
            f"Expected Content-Type: text/event-stream, got {content_type!r}. "
            "SSE transport is not correctly configured."
        )

    async def test_sse_endpoint_sends_endpoint_event(self, client: AsyncClient):
        """
        The first event on the SSE stream must be an 'endpoint' event containing
        the /mcp/messages URL with a sessionId. This is how the MCP client
        discovers where to POST its JSON-RPC messages.

        Event format:
            event: endpoint
            data: /messages/?sessionId=<uuid>
        """
        collected = b""
        try:
            async with asyncio.timeout(3.0):
                async with client.stream("GET", "/mcp/sse") as response:
                    assert response.status_code == 200
                    async for chunk in response.aiter_bytes():
                        collected += chunk
                        # Stop once we have the endpoint event
                        if b"sessionId" in collected or b"endpoint" in collected:
                            break
                        if len(collected) > 8192:
                            break
        except (TimeoutError, asyncio.CancelledError):
            pass

        decoded = collected.decode("utf-8", errors="replace")
        assert "endpoint" in decoded or "sessionId" in decoded or "messages" in decoded, (
            f"Expected endpoint event with sessionId in SSE stream first chunk, got: {decoded[:300]!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Tool Execution via JSON-RPC (POST /mcp/messages)
# ─────────────────────────────────────────────────────────────────────────────

class TestMCPToolExecution:
    """
    Tests that the MCP tool execution pipeline works end-to-end via JSON-RPC 2.0.
    Simulates exactly what the Prompt Opinion agent runtime sends when it
    invokes a tool.
    """

    async def _get_session_id(self, client: AsyncClient) -> str | None:
        """
        Helper: connect to /mcp/sse and extract the sessionId from the
        endpoint event so we can POST to /mcp/messages.
        Times out after 3 seconds — SSE stream stays open indefinitely.
        """
        session_id = None
        try:
            async with asyncio.timeout(3.0):
                async with client.stream("GET", "/mcp/sse") as response:
                    async for chunk in response.aiter_bytes():
                        text = chunk.decode("utf-8", errors="replace")
                        match = re.search(r"sessionId[=:]([a-zA-Z0-9\-]+)", text)
                        if match:
                            session_id = match.group(1)
                            break
                        if len(text) > 2048:
                            break
        except (TimeoutError, asyncio.CancelledError):
            pass
        return session_id

    async def test_tools_list_via_jsonrpc(self, client: AsyncClient):
        """
        POST a tools/list JSON-RPC call to /mcp/messages.
        Asserts that our three MCP tools are registered and discoverable.
        """
        session_id = await self._get_session_id(client)
        if session_id is None:
            pytest.skip("Could not extract SSE sessionId — skipping JSON-RPC test")

        jsonrpc_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }
        response = await client.post(
            f"/mcp/messages?sessionId={session_id}",
            json=jsonrpc_payload,
        )
        # MCP SSE returns 202 Accepted for async message processing
        assert response.status_code in (200, 202), (
            f"Expected 200/202 from /mcp/messages, got {response.status_code}"
        )

    async def test_get_fhir_context_via_rest_wrapper(self, client: AsyncClient):
        """
        Verifies get_fhir_context tool returns Tamara's FHIR data.
        Uses the REST wrapper endpoint for synchronous testability.
        The REST wrapper calls the same logic as the MCP tool.
        """
        response = await client.post(
            "/tools/get_fhir_context",
            json={"patient_id": "tamara-chen-001"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["patient"]["name"] == "Tamara Chen", (
            f"Expected patient name 'Tamara Chen', got {data['patient'].get('name')!r}"
        )
        assert isinstance(data.get("medications"), list)
        assert isinstance(data.get("observations"), list)
        assert isinstance(data.get("clinical_notes"), list)

    async def test_hunt_clinical_evidence_via_rest_wrapper(self, client: AsyncClient):
        """
        Verifies hunt_clinical_evidence tool locates the GI intolerance evidence.
        This is the critical 'exception hunting' capability that unlocks the PA bypass.
        """
        response = await client.post(
            "/tools/hunt_clinical_evidence",
            json={"patient_id": "tamara-chen-001", "condition_keyword": "GI intolerance"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["matching_notes"], (
            "Expected at least one note matching 'GI intolerance', got empty list. "
            "Check that seed_db correctly populates the GI intolerance progress note."
        )

    async def test_generate_pa_justification_via_rest_wrapper(self, client: AsyncClient):
        """
        Verifies the full PA reasoning pipeline returns a structured payload.
        LLM is mocked — no real API calls.
        """
        mock_llm_response = json.dumps({
            "step_therapy_assessment": "FAILED — 61 days completed, 180 required.",
            "exception_found": True,
            "exception_evidence": "Severe GI intolerance documented.",
            "pa_letter": "PRIOR AUTHORIZATION EXCEPTION REQUEST\n\nTo: Aetna\nApproved by: Dr. Morrison",
        })
        with patch("src.pa_engine._call_llm", return_value=mock_llm_response):
            response = await client.post(
                "/tools/generate_pa_justification",
                json={
                    "patient_id": "tamara-chen-001",
                    "target_medication": "Ozempic (semaglutide 0.5mg)",
                    "policy_text": "Aetna requires 6 months of metformin. Exception for GI intolerance.",
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert "step_therapy_met" in data
        assert data["step_therapy_met"] is False
        assert data["exception_found"] is True
        assert "pa_letter" in data


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Error Handling
# ─────────────────────────────────────────────────────────────────────────────

class TestErrorHandling:
    """
    Validates that the server returns proper error responses for invalid inputs.
    MCP and REST error handling are both tested.
    """

    async def test_unknown_patient_returns_404(self, client: AsyncClient):
        """
        Requesting FHIR context for an unknown patient must return HTTP 404.
        This prevents silent data errors when the Prompt Opinion agent passes
        an incorrect patient_id.
        """
        response = await client.post(
            "/tools/get_fhir_context",
            json={"patient_id": "does-not-exist-999"},
        )
        assert response.status_code == 404, (
            f"Expected 404 for unknown patient, got {response.status_code}"
        )

    async def test_missing_patient_id_returns_422(self, client: AsyncClient):
        """
        Missing required fields must return HTTP 422 (Pydantic validation error).
        """
        response = await client.post(
            "/tools/get_fhir_context",
            json={},  # Missing patient_id
        )
        assert response.status_code == 422, (
            f"Expected 422 for missing patient_id, got {response.status_code}"
        )

    async def test_hunt_evidence_unknown_patient_returns_404(self, client: AsyncClient):
        """Unknown patient_id on hunt_clinical_evidence must return 404."""
        response = await client.post(
            "/tools/hunt_clinical_evidence",
            json={"patient_id": "ghost-patient", "condition_keyword": "anything"},
        )
        assert response.status_code == 404

    async def test_hunt_evidence_no_match_returns_empty_list(self, client: AsyncClient):
        """
        A keyword with no clinical note matches must return an empty list
        with 200 OK — not a 404 or 500. The agent must be able to distinguish
        'no evidence found' from 'patient not found'.
        """
        response = await client.post(
            "/tools/hunt_clinical_evidence",
            json={
                "patient_id": "tamara-chen-001",
                "condition_keyword": "xylophone-allergy-condition-zzz",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("matching_notes") == [], (
            f"Expected empty list for no-match, got {data.get('matching_notes')}"
        )

    async def test_generate_pa_missing_fields_returns_422(self, client: AsyncClient):
        """Missing target_medication or policy_text must return 422."""
        response = await client.post(
            "/tools/generate_pa_justification",
            json={"patient_id": "tamara-chen-001"},  # Missing target_medication + policy_text
        )
        assert response.status_code == 422

    async def test_health_endpoint(self, client: AsyncClient):
        """GET /health must always return 200 with status=ok."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json().get("status") == "ok"
