"""
tests/wait_utils.py — Robust polling and retry logic using the Tenacity library.
"""
import httpx
from tenacity import retry, stop_after_delay, wait_fixed, retry_if_exception_type
import asyncio

def wait_for_url_ready(url: str, timeout: float = 10.0, interval: float = 0.2):
    """
    Synchronous polling until a URL returns 200 OK using tenacity.
    """
    from tenacity import Retrying
    
    try:
        for attempt in Retrying(
            stop=stop_after_delay(timeout),
            wait=wait_fixed(interval),
            retry=retry_if_exception_type(Exception),
            reraise=True
        ):
            with attempt:
                r = httpx.get(url, timeout=1.0)
                if r.status_code != 200:
                    raise Exception(f"Status {r.status_code}")
                return True
    except Exception as e:
        raise TimeoutError(f"URL {url} did not become ready within {timeout}s") from e

async def async_wait_for_condition(condition_fn, timeout: float = 5.0, interval: float = 0.1):
    """
    Asynchronous polling until condition_fn() returns true-ish using tenacity.
    """
    from tenacity.asyncio import AsyncRetrying
    
    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_delay(timeout),
            wait=wait_fixed(interval),
            reraise=True
        ):
            with attempt:
                if not condition_fn():
                    raise Exception("Condition not met")
                return True
    except Exception as e:
        raise TimeoutError(f"Condition not met within {timeout}s") from e
