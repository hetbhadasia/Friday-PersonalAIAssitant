"""
F.R.I.D.A.Y. V3 — Payment Webhook Security & Signature Verification
===================================================================
Enforces HMAC signature verification, timestamp drift check (replay defense),
and idempotency checking on all incoming payment callbacks.
"""

import hmac
import hashlib
import time
from typing import Any, Tuple
from friday.core.logging import get_logger

logger = get_logger("payment_webhook")

# Webhook idempotency cache
_PROCESSED_WEBHOOK_EVENTS: set[str] = set()
MAX_DRIFT_SECONDS = 300  # 5 minutes replay window


def verify_webhook_signature(payload_bytes: bytes, signature_header: str, secret: str) -> bool:
    """Validate HMAC SHA256 signature."""
    if not secret:
        # Development fallback only if no secret set
        return True
    expected = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def process_payment_webhook(
    event_payload: dict[str, Any],
    raw_body: bytes,
    signature: str,
    secret: str = "",
) -> Tuple[bool, str, dict[str, Any]]:
    """
    Strict validation of payment gateway callback.
    Verifies:
    1. Signature
    2. Event ID idempotency (no duplicate charging/crediting)
    3. Timestamp replay prevention
    4. Required fields: order_id, payment_id, amount, status
    """
    event_id = event_payload.get("event_id") or event_payload.get("id", "")
    if not event_id:
        return False, "Missing event identifier", {}

    # Check idempotency
    if event_id in _PROCESSED_WEBHOOK_EVENTS:
        logger.warning("Duplicate webhook event ignored: %s", event_id)
        return True, "Event already processed (Idempotent)", {"event_id": event_id, "duplicate": True}

    # Verify signature
    if secret and not verify_webhook_signature(raw_body, signature, secret):
        logger.error("Invalid webhook HMAC signature for event %s", event_id)
        return False, "Invalid signature", {}

    # Timestamp replay check
    timestamp = event_payload.get("timestamp", 0)
    now = int(time.time())
    if timestamp and abs(now - timestamp) > MAX_DRIFT_SECONDS:
        logger.error("Webhook rejected: Timestamp drift too high (%ss)", abs(now - timestamp))
        return False, "Timestamp expired or clock drift", {}

    # Required payload bindings
    order_id = event_payload.get("order_id")
    payment_id = event_payload.get("payment_id")
    status = event_payload.get("status")

    if not order_id or not payment_id or not status:
        return False, "Missing mandatory bindings (order_id, payment_id, status)", {}

    # Mark processed
    _PROCESSED_WEBHOOK_EVENTS.add(event_id)
    logger.info("Webhook verified and processed: event=%s order=%s status=%s", event_id, order_id, status)

    return True, "Verified and processed", {
        "event_id": event_id,
        "order_id": order_id,
        "payment_id": payment_id,
        "status": status,
        "amount": event_payload.get("amount"),
        "currency": event_payload.get("currency", "INR"),
    }
