"""
tests/test_wait_utils.py — Unit tests for the custom wait_utils implementation.
"""
import pytest
import time
import asyncio
from unittest.mock import MagicMock, patch
from tests.wait_utils import wait_for_url_ready, async_wait_for_condition

class TestWaitUtilsBaseline:
    def test_wait_for_url_ready_success(self):
        """Mock successful poll after failures."""
        with patch("httpx.get") as mock_get:
            # 2 failures, then 1 success
            mock_responses = [Exception("Failed"), Exception("Failed"), MagicMock(status_code=200)]
            mock_get.side_effect = mock_responses
            
            assert wait_for_url_ready("http://localhost/test", timeout=1.0, interval=0.1) is True
            assert mock_get.call_count == 3

    def test_wait_for_url_ready_timeout(self):
        """Mock polling failures until timeout."""
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = Exception("Failed")
            
            with pytest.raises(TimeoutError):
                wait_for_url_ready("http://localhost/test", timeout=0.3, interval=0.1)

    @pytest.mark.asyncio
    async def test_async_wait_for_condition_success(self):
        """Mock successful condition after failures."""
        calls = []
        def condition_fn():
            calls.append(1)
            return len(calls) >= 3
            
        assert await async_wait_for_condition(condition_fn, timeout=1.0, interval=0.1) is True
        assert len(calls) == 3

    @pytest.mark.asyncio
    async def test_async_wait_for_condition_timeout(self):
        """Mock condition failures until timeout."""
        def condition_fn():
            return False
            
        with pytest.raises(TimeoutError):
            await async_wait_for_condition(condition_fn, timeout=0.3, interval=0.1)
