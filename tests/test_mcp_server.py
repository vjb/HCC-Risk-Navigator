"""
tests/test_mcp_server.py — MCP Server Transport & Tool Tests
=============================================================
Tests for the HTTP/SSE MCP transport (for Prompt Opinion / ngrok integration).

Strategy:
  - REST wrapper tests: Use httpx.ASGITransport (fast, reliable, in-process).
  - SSE transport tests: Use a real uvicorn process on a random port — this is
    the only correct way to test SSE because it requires two concurrent connections
    (GET /mcp/sse + POST /mcp/messages), which ASGI transport cannot handle.
"""
from __future__ import annotations

import asyncio
import json
import re
import socket
import subprocess
import sys
import time
import os
from datetime import date, timedelta
from unittest.mock import patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from src.models import ClinicalNote, Condition, Patient


# ─────────────────────────────────────────────────────────────────────────────
# Shared Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def seeded_app(tmp_path_factory):
    """
    Creates a fresh in-memory SQLite database, seeds it, and returns the
    FastAPI app configured to use that DB.
    """
    import os
    db_path = tmp_path_factory.mktemp("mcp_test_db") / "test_ehr.sqlite"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    # Re-import after env setup
    from src.database import engine, init_db
    from src.models import Base
    Base.metadata.create_all(bind=engine)

    from sqlalchemy.orm import Session
    with Session(engine) as session:
        from scripts.seed_db import seed
        seed(session)

    from src.server import app
    return app


@pytest.fixture()
async def client(seeded_app):
    """In-process HTTPX client for REST endpoint tests."""
    async with AsyncClient(
        transport=ASGITransport(app=seeded_app),
        base_url="http://localhost",
        headers={"Host": "localhost"},
    ) as ac:
        yield ac


def _free_port() -> int:
    """Find an available TCP port for the live test server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server_url(seeded_app, tmp_path_factory):
    """
    Starts a REAL uvicorn process for SSE transport tests.
    SSE testing requires two concurrent connections, which ASGI transport cannot do.
    Yields the base URL string (e.g. 'http://127.0.0.1:18321').
    """
    port = _free_port()
    db_url = os.environ.get("DATABASE_URL", "")

    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "src.server:app",
            "--host", "127.0.0.1",
            "--port", str(port),
            "--log-level", "warning",
        ],
        env={**os.environ, "DATABASE_URL": db_url},  # Pass DB path to subprocess
    )

    # Wait for server to be ready
    deadline = time.time() + 10.0
    while time.time() < deadline:
        try:
            r = httpx.get(f"http://127.0.0.1:{port}/health", timeout=1.0)
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(0.2)
    else:
        proc.terminate()
        pytest.fail("Live uvicorn server failed to start within 10 seconds")

    yield f"http://127.0.0.1:{port}"

    proc.terminate()
    proc.wait(timeout=5)


# ─────────────────────────────────────────────────────────────────────────────
# Health Check & Basic Endpoints
# ─────────────────────────────────────────────────────────────────────────────

class TestHealthAndBasic:
    async def test_health_endpoint_returns_200(self, client):
        r = await client.get("/health")
        assert r.status_code == 200

    async def test_health_returns_ok_status(self, client):
        r = await client.get("/health")
        data = r.json()
        assert data["status"] == "ok"

    async def test_docs_endpoint_accessible(self, client):
        r = await client.get("/docs")
        assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# REST Wrapper Tests — audit_hcc_opportunities tool via POST /tools/*
# ─────────────────────────────────────────────────────────────────────────────

MOCK_AUDIT_RESULT = json.dumps({
    "gaps": [{
        "suspected_icd10": "E11.40",
        "suspected_hcc": 18,
        "description": "Type 2 diabetes mellitus with diabetic neuropathy",
        "evidence_quote": "burning sensation in both feet",
        "clinical_rationale": "Bilateral neuropathy symptoms with Gabapentin supports E11.40.",
        "raf_delta": 0.302,
        "confidence": "HIGH",
    }],
    "audit_summary": "Coding gap: E11.40 missing from problem list.",
})

class TestHCCAuditTool:
    async def test_audit_tool_returns_200(self, client):
        with patch("src.hcc_engine._call_llm", return_value=MOCK_AUDIT_RESULT):
            r = await client.post(
                "/tools/audit_hcc_opportunities",
                json={"patient_id": "tamara-williams-001"},
            )
        assert r.status_code == 200

    async def test_audit_identifies_e11_40_gap(self, client):
        with patch("src.hcc_engine._call_llm", return_value=MOCK_AUDIT_RESULT):
            r = await client.post(
                "/tools/audit_hcc_opportunities",
                json={"patient_id": "tamara-williams-001"},
            )
        data = r.json()
        gap_codes = [g["suspected_icd10"] for g in data.get("gaps", [])]
        assert "E11.40" in gap_codes

    async def test_audit_returns_current_raf(self, client):
        with patch("src.hcc_engine._call_llm", return_value=MOCK_AUDIT_RESULT):
            r = await client.post(
                "/tools/audit_hcc_opportunities",
                json={"patient_id": "tamara-williams-001"},
            )
        data = r.json()
        assert "current_raf" in data
        assert abs(data["current_raf"] - 0.104) < 0.001

    async def test_audit_returns_projected_raf(self, client):
        with patch("src.hcc_engine._call_llm", return_value=MOCK_AUDIT_RESULT):
            r = await client.post(
                "/tools/audit_hcc_opportunities",
                json={"patient_id": "tamara-williams-001"},
            )
        data = r.json()
        assert "projected_raf" in data
        assert data["projected_raf"] > data["current_raf"]


class TestErrorHandling:
    async def test_unknown_patient_returns_404(self, client):
        r = await client.post(
            "/tools/audit_hcc_opportunities",
            json={"patient_id": "nonexistent-000"},
        )
        assert r.status_code == 404

    async def test_missing_patient_id_returns_422(self, client):
        r = await client.post("/tools/audit_hcc_opportunities", json={})
        assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# SSE Transport Tests — real uvicorn process
# ─────────────────────────────────────────────────────────────────────────────

class TestSSETransport:
    """
    Tests for the MCP SSE endpoints using a real uvicorn process.
    ASGI transport cannot be used here because SSE requires TWO concurrent
    connections: one for GET /mcp/sse (stream) and one for POST /mcp/messages.
    """

    def test_sse_endpoint_returns_200(self, live_server_url):
        """GET /mcp/sse must start a streaming 200 response."""
        with httpx.stream("GET", f"{live_server_url}/mcp/sse", timeout=5.0) as r:
            assert r.status_code == 200

    def test_sse_endpoint_content_type(self, live_server_url):
        """GET /mcp/sse must return Content-Type: text/event-stream."""
        with httpx.stream("GET", f"{live_server_url}/mcp/sse", timeout=5.0) as r:
            assert "text/event-stream" in r.headers.get("content-type", "")

    def test_sse_stream_sends_endpoint_event(self, live_server_url):
        """
        The first SSE event must be an 'endpoint' event containing a sessionId.
        This is how the MCP client discovers where to POST its JSON-RPC calls.
        """
        collected = ""
        with httpx.stream("GET", f"{live_server_url}/mcp/sse", timeout=5.0) as r:
            for chunk in r.iter_text():
                collected += chunk
                if "sessionId" in collected or "endpoint" in collected:
                    break
                if len(collected) > 4096:
                    break
        assert "sessionId" in collected or "messages" in collected, (
            f"Expected endpoint event in SSE stream, got: {collected[:200]!r}"
        )

    async def test_jsonrpc_tools_list_via_sse(self, live_server_url):
        """
        Full MCP JSON-RPC round-trip over SSE transport:
          1. GET /mcp/sse → receive endpoint event + sessionId
          2. POST /mcp/messages?sessionId=X with initialize request
          3. POST /mcp/messages?sessionId=X with tools/list request
          4. Assert tools/list response contains audit_hcc_opportunities
        """
        session_id = None
        sse_task_done = asyncio.Event()

        async def collect_sse_session_id():
            nonlocal session_id
            async with httpx.AsyncClient(timeout=10.0) as hc:
                async with hc.stream("GET", f"{live_server_url}/mcp/sse") as resp:
                    async for line in resp.aiter_lines():
                        if "sessionId" in line:
                            m = re.search(r"sessionId=([A-Za-z0-9_\-]+)", line)
                            if m:
                                session_id = m.group(1)
                                break
                    await sse_task_done.wait()

        sse_task = asyncio.create_task(collect_sse_session_id())

        # Wait for sessionId
        for _ in range(50):
            if session_id:
                break
            await asyncio.sleep(0.1)

        assert session_id, "SSE transport did not send an endpoint event with sessionId"

        async with httpx.AsyncClient(timeout=5.0) as hc:
            # MCP initialize
            r1 = await hc.post(
                f"{live_server_url}/mcp/messages",
                params={"sessionId": session_id},
                json={
                    "jsonrpc": "2.0", "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test-client", "version": "0.1"},
                    },
                },
                headers={"Content-Type": "application/json"},
            )
            assert r1.status_code in (200, 202), f"initialize failed: {r1.status_code} {r1.text}"

            # MCP initialized notification
            await hc.post(
                f"{live_server_url}/mcp/messages",
                params={"sessionId": session_id},
                json={"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
                headers={"Content-Type": "application/json"},
            )

            # tools/list
            r2 = await hc.post(
                f"{live_server_url}/mcp/messages",
                params={"sessionId": session_id},
                json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                headers={"Content-Type": "application/json"},
            )
            assert r2.status_code in (200, 202)

        # Give the SSE stream time to receive the tool list response
        await asyncio.sleep(0.5)
        sse_task_done.set()

        try:
            await asyncio.wait_for(sse_task, timeout=3.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            sse_task.cancel()
