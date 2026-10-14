"""
F.R.I.D.A.Y. V2 — Resilience Utilities
=======================================
Retry with exponential backoff, circuit breaker, and timeout helpers.
"""

import asyncio
import time
from typing import Callable, Any
from functools import wraps

from friday.core.logging import get_logger
from friday.core.errors import NetworkError, ProviderError

logger = get_logger("resilience")


class CircuitBreaker:
    """
    Lightweight circuit breaker.
    
    States:
      CLOSED   → normal operation, failures counted
      OPEN     → requests immediately rejected
      HALF_OPEN → one probe allowed, success → CLOSED, failure → OPEN
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(self, name: str, failure_threshold: int = 5, reset_timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._state = self.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> str:
        if self._state == self.OPEN:
            if time.monotonic() - self._last_failure_time >= self.reset_timeout:
                return self.HALF_OPEN
        return self._state

    @property
    def is_available(self) -> bool:
        return self.state != self.OPEN

    async def record_success(self):
        async with self._lock:
            self._failure_count = 0
            self._state = self.CLOSED

    async def record_failure(self):
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._failure_count >= self.failure_threshold:
                self._state = self.OPEN
                logger.warning(
                    "Circuit breaker OPEN for %s after %d failures",
                    self.name, self._failure_count,
                )

    def reset(self):
        self._state = self.CLOSED
        self._failure_count = 0


async def retry_async(
    func: Callable,
    *args,
    max_retries: int = 3,
    backoff_base: float = 1.5,
    retryable_exceptions: tuple = (Exception,),
    operation_name: str = "",
    **kwargs,
) -> Any:
    """
    Retry an async function with exponential backoff.
    
    Returns the result on success, raises the last exception on exhaustion.
    """
    last_exception = None
    name = operation_name or getattr(func, "__name__", "unknown")

    for attempt in range(1, max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except retryable_exceptions as exc:
            last_exception = exc
            if attempt < max_retries:
                delay = backoff_base ** (attempt - 1)
                logger.warning(
                    "%s attempt %d/%d failed: %s — retrying in %.1fs",
                    name, attempt, max_retries, exc, delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "%s failed after %d attempts: %s",
                    name, max_retries, exc,
                )

    raise last_exception


def with_timeout(timeout_seconds: float, operation_name: str = ""):
    """Decorator that wraps an async function with asyncio.wait_for."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                name = operation_name or func.__name__
                logger.error("%s timed out after %.1fs", name, timeout_seconds)
                raise

        return wrapper

    return decorator
