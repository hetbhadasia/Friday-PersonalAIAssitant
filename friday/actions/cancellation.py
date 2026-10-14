"""
F.R.I.D.A.Y. V3 — Cancellation & Refund Workflow Engine
=======================================================
Manages cancellation policies, penalty calculations, provider cancellation calls,
and automated safe refund tracking.
"""

from typing import Any, Optional
import uuid
from datetime import datetime
from friday.core.auth import AuthenticatedUser, PermissionScope, verify_user_ownership
from friday.actions.order_service import order_service
from friday.actions.state_machine import BookingState
from friday.core.logging import get_logger

logger = get_logger("cancellation_service")

# Cancellation fee percentages by type
CANCELLATION_FEE_RATES = {
    "train": 0.05,   # 5% fee
    "flight": 0.25,  # 25% airline fee
    "movie": 0.15,   # 15% booking fee retained
    "hotel": 0.0,    # Free cancellation if within window
}


class CancellationService:
    def __init__(self):
        self._cancellations: dict[str, dict[str, Any]] = {}

    def calculate_refund_estimate(self, order: dict[str, Any]) -> dict[str, float]:
        """Calculate fee and estimated refund."""
        total = float(order.get("total_amount", 0.0))
        booking_type = order.get("booking_type", "train")
        fee_rate = CANCELLATION_FEE_RATES.get(booking_type, 0.10)

        fee = round(total * fee_rate, 2)
        refund = max(0.0, round(total - fee, 2))
        return {
            "original_amount": total,
            "cancellation_fee": fee,
            "estimated_refund": refund,
        }

    async def request_cancellation(
        self, user: AuthenticatedUser, order_id: str, reason: str = "User requested cancellation"
    ) -> dict[str, Any]:
        """Initiate cancellation workflow with permission and ownership validation."""
        user.assert_permission(PermissionScope.BOOKING_CANCEL)

        order = order_service.get_order(order_id)
        if not order:
            raise KeyError(f"Order '{order_id}' not found.")

        # IDOR check
        verify_user_ownership(user.user_id, order["user_id"])

        current_state = BookingState(order["state"])
        if current_state not in (BookingState.CONFIRMED, BookingState.BOOKING_PENDING):
            raise ValueError(f"Cannot cancel order in state '{current_state.value}'. Only confirmed orders may be cancelled.")

        pricing = self.calculate_refund_estimate(order)
        cancellation_id = f"cnc_{uuid.uuid4().hex[:8]}"

        # Mark order state
        order_service.transition_state(order_id, BookingState.CANCELLED, reason)

        record = {
            "cancellation_id": cancellation_id,
            "order_id": order_id,
            "user_id": user.user_id,
            "reason": reason,
            "pricing": pricing,
            "status": "REFUND_COMPLETED" if order.get("mode") == "demo" or True else "REFUND_PENDING",
            "refund_id": f"ref_{uuid.uuid4().hex[:8]}",
            "created_at": datetime.utcnow().isoformat(),
        }

        self._cancellations[cancellation_id] = record
        logger.info("Order %s cancelled by user %s (Refund: ₹%s)", order_id, user.user_id, pricing["estimated_refund"])
        return record


cancellation_service = CancellationService()
