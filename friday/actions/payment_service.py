"""
F.R.I.D.A.Y. V3 — Payment Gateway Architecture & PCI Voice Isolation
====================================================================
Strict security rule: Voice stream and LLM context NEVER handle card numbers,
CVVs, UPI PINs, passwords, or OTPs.
Only out-of-band checkout sessions are issued.
"""

from abc import ABC, abstractmethod
import uuid
import hmac
import hashlib
from datetime import datetime
from typing import Any, Optional
from friday.actions.models import PaymentSession, PaymentStatus
from friday.config import config
from friday.core.logging import get_logger

logger = get_logger("payment_gateway")


class PaymentProvider(ABC):
    """Abstract interface for payment gateways."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def is_real_gateway(self) -> bool:
        pass

    @abstractmethod
    async def create_checkout_session(
        self, order_id: str, amount: float, currency: str, user_id: str
    ) -> PaymentSession:
        pass

    @abstractmethod
    async def verify_payment(self, payment_id: str) -> dict[str, Any]:
        pass

    @abstractmethod
    async def refund_payment(self, payment_id: str, amount: float, reason: str = "") -> dict[str, Any]:
        pass


class MockPaymentProvider(PaymentProvider):
    """Safe mock payment provider for development and testing."""

    def __init__(self):
        self._sessions: dict[str, PaymentSession] = {}

    @property
    def provider_name(self) -> str:
        return "MockPaymentProvider"

    @property
    def is_real_gateway(self) -> bool:
        return False

    async def create_checkout_session(
        self, order_id: str, amount: float, currency: str = "INR", user_id: str = "iron-man"
    ) -> PaymentSession:
        payment_id = f"pay_mock_{uuid.uuid4().hex[:10]}"
        checkout_url = f"http://127.0.0.1:8080/api/v1/payments/{payment_id}/checkout"

        session = PaymentSession(
            payment_id=payment_id,
            order_id=order_id,
            amount=amount,
            currency=currency,
            status=PaymentStatus.PENDING,
            checkout_url=checkout_url,
        )
        self._sessions[payment_id] = session
        logger.info("Mock payment session created: %s for order %s (₹%s)", payment_id, order_id, amount)
        return session

    async def verify_payment(self, payment_id: str) -> dict[str, Any]:
        session = self._sessions.get(payment_id)
        if not session:
            return {"verified": False, "status": "not_found"}
        return {
            "verified": session.status == PaymentStatus.PAID,
            "status": session.status.value,
            "amount": session.amount,
            "currency": session.currency,
        }

    async def complete_mock_payment(self, payment_id: str) -> PaymentSession:
        session = self._sessions.get(payment_id)
        if not session:
            raise KeyError(f"Payment session '{payment_id}' not found.")
        session.status = PaymentStatus.PAID
        logger.info("Mock payment %s marked PAID", payment_id)
        return session

    async def refund_payment(self, payment_id: str, amount: float, reason: str = "") -> dict[str, Any]:
        session = self._sessions.get(payment_id)
        if not session:
            raise KeyError(f"Payment session '{payment_id}' not found.")
        session.status = PaymentStatus.REFUNDED if hasattr(PaymentStatus, "REFUNDED") else PaymentStatus.CANCELLED
        return {
            "mode": "demo",
            "is_real_payment": False,
            "refund_id": f"ref_mock_{uuid.uuid4().hex[:8]}",
            "payment_id": payment_id,
            "refund_amount": amount,
            "status": "refund_completed",
            "message": "Simulated mock refund successfully processed.",
        }


class RazorpayProvider(PaymentProvider):
    """Production gateway stub for Razorpay — only activated when explicitly configured."""

    def __init__(self, key_id: str = "", key_secret: str = ""):
        self.key_id = key_id
        self.key_secret = key_secret

    @property
    def provider_name(self) -> str:
        return "Razorpay"

    @property
    def is_real_gateway(self) -> bool:
        return True

    async def create_checkout_session(
        self, order_id: str, amount: float, currency: str, user_id: str
    ) -> PaymentSession:
        if not self.key_id or not self.key_secret:
            raise RuntimeError("Razorpay credentials not configured in environment.")
        # Prepared for real gateway integration when authorized keys provided
        raise NotImplementedError("Real Razorpay API requires production partner authorization.")

    async def verify_payment(self, payment_id: str) -> dict[str, Any]:
        raise NotImplementedError("Real Razorpay verification requires configured API keys.")

    async def refund_payment(self, payment_id: str, amount: float, reason: str = "") -> dict[str, Any]:
        raise NotImplementedError("Real Razorpay refund requires configured API keys.")


class CashfreeProvider(PaymentProvider):
    """Production gateway stub for Cashfree — only activated when explicitly configured."""

    def __init__(self, app_id: str = "", secret_key: str = ""):
        self.app_id = app_id
        self.secret_key = secret_key

    @property
    def provider_name(self) -> str:
        return "Cashfree"

    @property
    def is_real_gateway(self) -> bool:
        return True

    async def create_checkout_session(
        self, order_id: str, amount: float, currency: str, user_id: str
    ) -> PaymentSession:
        raise NotImplementedError("Real Cashfree API requires production credentials.")

    async def verify_payment(self, payment_id: str) -> dict[str, Any]:
        raise NotImplementedError("Real Cashfree API requires production credentials.")

    async def refund_payment(self, payment_id: str, amount: float, reason: str = "") -> dict[str, Any]:
        raise NotImplementedError("Real Cashfree API requires production credentials.")


# Active Payment Manager
class PaymentManager:
    def __init__(self):
        self.mock_provider = MockPaymentProvider()
        # Default is safe mock
        self._active_provider: PaymentProvider = self.mock_provider

    def get_provider(self) -> PaymentProvider:
        if getattr(config.features, "ENABLE_REAL_PAYMENT", False):
            # If user configured real payment, load gateway
            return self._active_provider
        return self.mock_provider


payment_manager = PaymentManager()
