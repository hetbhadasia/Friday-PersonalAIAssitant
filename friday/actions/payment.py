"""
F.R.I.D.A.Y. V2 — Secure Payment Service
=========================================
Strict PCI-DSS compliance and voice isolation architecture.
Raw credit card numbers, CVVs, UPI PINs, passwords, and OTPs are NEVER
handled or permitted through the LLM context or voice stream.

Payment works strictly via out-of-band checkout sessions:
1. LLM initiates a PaymentSession with order_id and amount.
2. An out-of-band hosted checkout URL / token is generated.
3. User completes payment externally (or via mock verification).
4. System records the verified result.
"""

import uuid
from typing import Any
from datetime import datetime
from friday.actions.models import PaymentSession, PaymentStatus
from friday.config import config
from friday.core.logging import get_logger

logger = get_logger("action_payment")

# In-memory store for active payment sessions
_PAYMENT_STORE: dict[str, PaymentSession] = {}


def create_payment_session(
    order_id: str,
    amount: float,
    currency: str = "INR",
) -> PaymentSession:
    """
    Create a secure out-of-band payment session.
    Returns session with safe checkout URL.
    """
    payment_id = f"pay_{uuid.uuid4().hex[:12]}"
    
    # In development/mock mode, provide a mock checkout URL
    checkout_url = f"http://127.0.0.1:8080/api/v1/payments/{payment_id}/checkout"

    session = PaymentSession(
        payment_id=payment_id,
        order_id=order_id,
        amount=amount,
        currency=currency,
        status=PaymentStatus.PENDING,
        checkout_url=checkout_url,
    )
    _PAYMENT_STORE[payment_id] = session
    logger.info("Payment session created: id=%s order=%s amount=%s %s", payment_id, order_id, amount, currency)
    return session


def get_payment_session(payment_id: str) -> PaymentSession | None:
    """Retrieve an existing payment session."""
    return _PAYMENT_STORE.get(payment_id)


def complete_mock_payment(payment_id: str) -> PaymentSession | None:
    """Simulate successful payment authorization for development/testing."""
    session = _PAYMENT_STORE.get(payment_id)
    if not session:
        return None

    session.status = PaymentStatus.PAID
    logger.info("Payment session authorized: id=%s", payment_id)
    return session


def list_payment_sessions() -> list[dict[str, Any]]:
    """List recent payment sessions."""
    return [s.to_dict() for s in _PAYMENT_STORE.values()]
