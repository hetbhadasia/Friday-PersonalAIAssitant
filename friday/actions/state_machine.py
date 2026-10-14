"""
F.R.I.D.A.Y. V3 — Booking State Machine
=======================================
Strict deterministic finite state machine governing the entire booking lifecycle.
Rejects any illegal transitions (e.g. PAYMENT_PENDING directly to CONFIRMED).
"""

from enum import Enum
from typing import Set


class BookingState(str, Enum):
    DRAFT = "DRAFT"
    SEARCHING = "SEARCHING"
    OPTION_SELECTED = "OPTION_SELECTED"
    REVALIDATING = "REVALIDATING"
    AWAITING_USER_CONFIRMATION = "AWAITING_USER_CONFIRMATION"
    PAYMENT_REQUIRED = "PAYMENT_REQUIRED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAYMENT_VERIFIED = "PAYMENT_VERIFIED"
    BOOKING_PENDING = "BOOKING_PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal booking state transition is attempted."""
    def __init__(self, from_state: BookingState, to_state: BookingState, reason: str = ""):
        msg = f"Illegal transition from '{from_state.value}' to '{to_state.value}'."
        if reason:
            msg += f" Reason: {reason}"
        super().__init__(msg)
        self.from_state = from_state
        self.to_state = to_state


# Formal transition matrix
VALID_TRANSITIONS: dict[BookingState, Set[BookingState]] = {
    BookingState.DRAFT: {
        BookingState.SEARCHING,
        BookingState.OPTION_SELECTED,
        BookingState.CANCELLED,
    },
    BookingState.SEARCHING: {
        BookingState.OPTION_SELECTED,
        BookingState.FAILED,
        BookingState.CANCELLED,
    },
    BookingState.OPTION_SELECTED: {
        BookingState.REVALIDATING,
        BookingState.CANCELLED,
    },
    BookingState.REVALIDATING: {
        BookingState.AWAITING_USER_CONFIRMATION,
        BookingState.FAILED,
        BookingState.CANCELLED,
    },
    BookingState.AWAITING_USER_CONFIRMATION: {
        BookingState.PAYMENT_REQUIRED,
        BookingState.CANCELLED,
        BookingState.EXPIRED,
    },
    BookingState.PAYMENT_REQUIRED: {
        BookingState.PAYMENT_PENDING,
        BookingState.CANCELLED,
        BookingState.EXPIRED,
    },
    BookingState.PAYMENT_PENDING: {
        BookingState.PAYMENT_VERIFIED,
        BookingState.FAILED,
        BookingState.EXPIRED,
        BookingState.CANCELLED,
    },
    BookingState.PAYMENT_VERIFIED: {
        BookingState.BOOKING_PENDING,
        BookingState.RECONCILIATION_REQUIRED,
        BookingState.FAILED,
    },
    BookingState.BOOKING_PENDING: {
        BookingState.CONFIRMED,
        BookingState.UNKNOWN,
        BookingState.FAILED,
        BookingState.RECONCILIATION_REQUIRED,
    },
    BookingState.CONFIRMED: {
        BookingState.CANCELLED,
    },
    BookingState.UNKNOWN: {
        BookingState.CONFIRMED,
        BookingState.RECONCILIATION_REQUIRED,
        BookingState.FAILED,
    },
    BookingState.RECONCILIATION_REQUIRED: {
        BookingState.CONFIRMED,
        BookingState.CANCELLED,
        BookingState.FAILED,
    },
    BookingState.FAILED: set(),
    BookingState.CANCELLED: set(),
    BookingState.EXPIRED: set(),
}


def can_transition(current_state: BookingState, next_state: BookingState) -> bool:
    """Check if state transition is legally allowed."""
    return next_state in VALID_TRANSITIONS.get(current_state, set())


def validate_transition(current_state: BookingState, next_state: BookingState, reason: str = "") -> None:
    """Validate transition and raise InvalidStateTransitionError if illegal."""
    if not can_transition(current_state, next_state):
        raise InvalidStateTransitionError(current_state, next_state, reason)
