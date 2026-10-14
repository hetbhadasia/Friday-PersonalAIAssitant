"""
F.R.I.D.A.Y. V2 — Action Domain Models
=======================================
Immutable data classes for bookings, orders, and payment sessions.
Strict security rule: Raw card details, CVVs, or PINs are NEVER accepted.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class BookingType(str, Enum):
    TRAIN = "train"
    FLIGHT = "flight"
    MOVIE = "movie"
    HOTEL = "hotel"


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BookingOrder:
    order_id: str
    booking_type: BookingType
    title: str
    description: str
    amount: float
    currency: str = "INR"
    status: BookingStatus = BookingStatus.PENDING
    payment_status: PaymentStatus = PaymentStatus.PENDING
    payment_session_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "booking_type": self.booking_type.value,
            "title": self.title,
            "description": self.description,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status.value,
            "payment_status": self.payment_status.value,
            "payment_session_id": self.payment_session_id,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class PaymentSession:
    payment_id: str
    order_id: str
    amount: float
    currency: str
    status: PaymentStatus = PaymentStatus.PENDING
    checkout_url: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "payment_id": self.payment_id,
            "order_id": self.order_id,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status.value,
            "checkout_url": self.checkout_url,
            "created_at": self.created_at,
        }
