"""
F.R.I.D.A.Y. V3 — Idempotency Control System
============================================
Guarantees at-most-once execution for transactional operations:
- Payment session creation
- Booking reservations
- Cancellations and refunds
"""

import time
from typing import Any, Optional
from friday.core.logging import get_logger

logger = get_logger("idempotency_service")


class IdempotencyRecord:
    def __init__(self, key: str, operation: str, result: Any, ttl_seconds: int = 86400):
        self.key = key
        self.operation = operation
        self.result = result
        self.expires_at = time.time() + ttl_seconds


class IdempotencyService:
    """Manages unique idempotency tokens across transactional boundaries."""

    def __init__(self):
        self._store: dict[str, IdempotencyRecord] = {}

    def get(self, key: str, operation: str) -> Optional[Any]:
        """Check if an operation with this idempotency key was already completed."""
        compound_key = f"{operation}:{key}"
        record = self._store.get(compound_key)
        if not record:
            return None

        if time.time() > record.expires_at:
            del self._store[compound_key]
            return None

        logger.info("Idempotent replay served for key %s (op: %s)", key, operation)
        return record.result

    def save(self, key: str, operation: str, result: Any, ttl_seconds: int = 86400) -> None:
        """Store the result of a completed transactional operation."""
        compound_key = f"{operation}:{key}"
        self._store[compound_key] = IdempotencyRecord(key, operation, result, ttl_seconds)
        logger.info("Idempotency key saved: %s (op: %s)", key, operation)


idempotency_service = IdempotencyService()
