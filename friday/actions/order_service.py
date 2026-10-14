"""
F.R.I.D.A.Y. V3 — Universal Order Service
=========================================
Authoritative server-side order lifecycle and pricing calculator.
Strict security rule: Never trust client/LLM-reported amounts.
Calculates taxes, fees, and currency binding strictly on the backend.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Optional
from friday.actions.models import BookingOrder, BookingType, BookingStatus, PaymentStatus
from friday.actions.state_machine import BookingState, validate_transition
from friday.core.logging import get_logger

logger = get_logger("order_service")

# Standard tax rate (GST 18%) and convenience fees
TAX_RATE = 0.18
CONVENIENCE_FEES = {
    BookingType.TRAIN: 40.0,
    BookingType.FLIGHT: 250.0,
    BookingType.MOVIE: 30.0,
    BookingType.HOTEL: 150.0,
}


class OrderService:
    """Universal service managing immutable order calculations and states."""

    def __init__(self):
        self._orders: dict[str, dict[str, Any]] = {}

    def calculate_totals(self, booking_type: BookingType, base_amount: float) -> dict[str, float]:
        """
        Authoritative server-side price calculation.
        Never trust amounts sent by clients or LLMs.
        """
        fee = CONVENIENCE_FEES.get(booking_type, 50.0)
        subtotal = base_amount + fee
        tax = round(subtotal * TAX_RATE, 2)
        total = round(subtotal + tax, 2)
        return {
            "base_fare": float(base_amount),
            "convenience_fee": float(fee),
            "tax_gst_18": float(tax),
            "total_amount": float(total),
        }

    def create_order_draft(
        self,
        user_id: str,
        booking_type: BookingType,
        title: str,
        description: str,
        base_amount: float,
        provider_name: str,
        metadata: dict[str, Any],
        currency: str = "INR",
        ttl_minutes: int = 15,
    ) -> dict[str, Any]:
        """Create a new authoritatively calculated order draft."""
        order_id = f"ord_{booking_type.value[:3]}_{uuid.uuid4().hex[:8]}"
        pricing = self.calculate_totals(booking_type, base_amount)
        expires_at = (datetime.utcnow() + timedelta(minutes=ttl_minutes)).isoformat()

        order_data = {
            "order_id": order_id,
            "user_id": user_id,
            "booking_type": booking_type.value,
            "title": title,
            "description": description,
            "provider_name": provider_name,
            "currency": currency,
            "pricing": pricing,
            "total_amount": pricing["total_amount"],
            "state": BookingState.DRAFT.value,
            "is_locked": False,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at,
            "metadata": metadata,
            "payment_id": None,
        }

        self._orders[order_id] = order_data
        logger.info("Order draft created: %s for user=%s total=%s %s", order_id, user_id, pricing["total_amount"], currency)
        return order_data

    def transition_state(self, order_id: str, next_state: BookingState, reason: str = "") -> dict[str, Any]:
        """Transition order state through the strict finite state machine."""
        order = self._orders.get(order_id)
        if not order:
            raise KeyError(f"Order '{order_id}' not found.")

        current = BookingState(order["state"])
        validate_transition(current, next_state, reason)

        order["state"] = next_state.value
        logger.info("Order %s transitioned: %s -> %s", order_id, current.value, next_state.value)
        return order

    def advance_order_lifecycle(self, order_id: str) -> dict[str, Any]:
        """
        Advance order through the formal legal states:
        DRAFT -> OPTION_SELECTED -> REVALIDATING -> AWAITING_USER_CONFIRMATION ->
        PAYMENT_REQUIRED -> PAYMENT_PENDING -> PAYMENT_VERIFIED -> BOOKING_PENDING -> CONFIRMED
        """
        states_sequence = [
            BookingState.OPTION_SELECTED,
            BookingState.REVALIDATING,
            BookingState.AWAITING_USER_CONFIRMATION,
            BookingState.PAYMENT_REQUIRED,
            BookingState.PAYMENT_PENDING,
            BookingState.PAYMENT_VERIFIED,
            BookingState.BOOKING_PENDING,
            BookingState.CONFIRMED,
        ]
        res = None
        for st in states_sequence:
            res = self.transition_state(order_id, st, f"Advancing lifecycle to {st.value}")
        return res

    def lock_order_for_payment(self, order_id: str) -> dict[str, Any]:
        """Lock order against further price/itinerary modifications before payment."""
        order = self._orders.get(order_id)
        if not order:
            raise KeyError(f"Order '{order_id}' not found.")

        # Transition state
        current = BookingState(order["state"])
        if current not in (BookingState.DRAFT, BookingState.AWAITING_USER_CONFIRMATION, BookingState.PAYMENT_REQUIRED):
            raise ValueError(f"Cannot lock order in state '{current.value}' for payment.")

        order["is_locked"] = True
        if current != BookingState.PAYMENT_REQUIRED:
            self.transition_state(order_id, BookingState.PAYMENT_REQUIRED, "Locked for payment checkout")

        return order

    def get_order(self, order_id: str) -> Optional[dict[str, Any]]:
        return self._orders.get(order_id)

    def list_user_orders(self, user_id: str, status: Optional[str] = None) -> list[dict[str, Any]]:
        """List orders filtered strictly by authenticated user."""
        res = [
            o for o in self._orders.values()
            if o["user_id"] == user_id
        ]
        if status:
            res = [o for o in res if o["state"].lower() == status.lower()]
        return list(reversed(res))


# Global singleton instance
order_service = OrderService()
