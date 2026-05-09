# Standard Library Enforcement & TDD Refactoring

## Overview
Identification and refactoring of "reinvented wheels" (custom retry/polling logic) into the industry-standard `tenacity` library. This improves deterministic test execution, readability, and maintainability across the HCC Risk Navigator codebase.

## Audit Findings
- **Anti-Pattern:** Inline custom polling loops using `while time.time() < deadline` and `time.sleep()`.
- **Locations:** `tests/test_mcp_server.py` (live server startup, SSE session discovery) and `tests/test_ui.py` (Streamlit server warmup).
- **Impacts:** Prone to flakiness, race conditions, and poor error reporting. Brittle `time.sleep(8)` calls lead to slow CI/CD pipelines.

## Refactoring Execution (TDD)
1. **Extraction:** Relocated manual logic into a centralized `tests/wait_utils.py`.
2. **Lock State:** Created `tests/test_wait_utils.py` with mock failure scenarios, establishing a Green baseline for the legacy implementation.
3. **Refactor:** Replaced manual loops with `tenacity.Retrying` and `tenacity.AsyncRetrying` engines.
4. **Verification:** Confirmed `tests/test_wait_utils.py` passed with the new implementation, ensuring the contract was perfectly maintained.

## Functional Fixes
While performaning the audit, several pre-existing test synchronization issues were identified and resolved:
- **UI Assertions:** Updated `tests/test_ui.py` to match the actual enterprise branding ("Clinic-Wide Performance" and "Run AI Chart Audit" button).
- **SSE Protocol:** Identified that the Server-Sent Events (SSE) data format used `session_id` (underscore) instead of `sessionId` (camelCase) and updated the extraction regex accordingly.
- **URL Consistency:** Added trailing slashes to SSE POST endpoints to match the FastAPI mount points precisely.

## Lessons Learned
- **Prefer Declarative Retries:** Libraries like `tenacity` provide declarative retry strategies (exponential backoff, jitter, specific exception filters) that are significantly more reliable than manual loops.
- **Synchronize Test Data:** UI tests often fail not due to logic errors but due to drifts in frontend labels; centralized branding tokens in a shared `constants.py` or similar could mitigate this.
- **Check External Protocol Specs:** When integrating with SDKs (like MCP/FastMCP), always log raw protocol data to verify naming conventions (e.g., snake_case vs camelCase) before building extraction logic.
