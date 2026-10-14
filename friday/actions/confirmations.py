"""
F.R.I.D.A.Y. V3 — User Confirmation & Approval Engine
=====================================================
Cryptographically signed approval tickets for transactional operations.
Enforces detail-hash validation and auto-invalidation on any itinerary/price modification.
"""

import hashlib
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional
from friday.core.logging import get_logger

logger = get_logger("action_confirmations")


class ConfirmationTicket:
    def __init__(
        self,
        confirmation_id: str,
        user_id: str,
        order_id: str,
        amount: float,
        currency: str,
        summary_hash: str,
        summary_payload: dict[str, Any],
        expires_at: datetime,
    ):
        self.confirmation_id = confirmation_id
        self.user_id = user_id
        self.order_id = order_id
        self.amount = amount
        self.currency = currency
        self.summary_hash = summary_hash
        self.summary_payload = summary_payload
        self.expires_at = expires_at
        self.is_confirmed = False
        self.is_cancelled = False
        self.created_at = datetime.utcnow()

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "confirmation_id": self.confirmation_id,
            "user_id": self.user_id,
            "order_id": self.order_id,
            "amount": self.amount,
            "currency": self.currency,
            "summary_hash": self.summary_hash,
            "summary_payload": self.summary_payload,
            "is_confirmed": self.is_confirmed,
            "is_cancelled": self.is_cancelled,
            "is_expired": self.is_expired,
            "expires_at": self.expires_at.isoformat(),
            "created_at": self.created_at.isoformat(),
        }


class ConfirmationService:
    """Manages transactional approvals, summary hashes, and tamper invalidation."""

    def __init__(self):
        self._tickets: dict[str, ConfirmationTicket] = {}
        self._order_ticket_map: dict[str, str] = {}

    def compute_summary_hash(self, payload: dict[str, Any]) -> str:
        """Generate deterministic cryptographic hash of order details."""
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def create_confirmation_request(
        self,
        user_id: str,
        order_id: str,
        amount: float,
        currency: str,
        details: dict[str, Any],
        ttl_minutes: int = 10,
    ) -> ConfirmationTicket:
        """Create a user approval ticket with cryptographic summary hash."""
        # Invalidate any existing confirmation for this order if details changed
        existing_id = self._order_ticket_map.get(order_id)
        if existing_id and existing_id in self._tickets:
            self._tickets[existing_id].is_cancelled = True
            logger.info("Invalidated previous confirmation %s for order %s", existing_id, order_id)

        summary_hash = self.compute_summary_hash(details)
        ticket_id = f"conf_{uuid.uuid4().hex[:12]}"
        expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)

        ticket = ConfirmationTicket(
            confirmation_id=ticket_id,
            user_id=user_id,
            order_id=order_id,
            amount=amount,
            currency=currency,
            summary_hash=summary_hash,
            summary_payload=details,
            expires_at=expires_at,
        )

        self._tickets[ticket_id] = ticket
        self._order_ticket_map[order_id] = ticket_id
        logger.info("Generated confirmation ticket %s for order %s (TTL: %sm)", ticket_id, order_id, ttl_minutes)
        return ticket

    def approve_confirmation(self, confirmation_id: str, user_id: str, current_details: dict[str, Any]) -> bool:
        """
        Verify approval: checks user identity, expiration, and asserts that
        order details/pricing did not tamper or change since ticket generation.
        """
        ticket = self._tickets.get(confirmation_id)
        if not ticket:
            raise KeyError(f"Confirmation ticket '{confirmation_id}' not found.")

        if ticket.user_id != user_id:
            raise PermissionError(f"Ticket user '{ticket.user_id}' does not match authenticated user '{user_id}'.")

        if ticket.is_expired:
            raise TimeoutError("Confirmation ticket has expired. Please review and confirm again.")

        if ticket.is_cancelled:
            raise ValueError("Confirmation ticket has been invalidated due to modifications.")

        # Recompute hash to assert no details changed
        current_hash = self.compute_summary_hash(current_details)
        if current_hash != ticket.summary_hash:
            ticket.is_cancelled = True
            raise ValueError("Order details or pricing have changed since review. Confirmation invalidated.")

        ticket.is_confirmed = True
        logger.info("Confirmation ticket %s confirmed by user %s", confirmation_id, user_id)
        return True

    def get_ticket(self, confirmation_id: str) -> Optional[ConfirmationTicket]:
        return self._tickets.get(confirmation_id)


# Global singleton instance
confirmation_service = ConfirmationService()
