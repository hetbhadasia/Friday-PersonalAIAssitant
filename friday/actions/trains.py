"""
F.R.I.D.A.Y. V3 — Train Booking Provider & Mock Implementation
==============================================================
Implements TrainProvider interface.
Strict demo isolation: All mock bookings are explicitly marked as DEMO,
and reference codes are prefixed with DEMO-TRAIN-XXXX.
"""

from typing import Any
import uuid
from datetime import datetime
from friday.actions.interfaces import TrainProvider, IntegrationCapability, ProviderEnvironment
from friday.core.logging import get_logger

logger = get_logger("action_trains")

MOCK_TRAIN_CATALOG = [
    {
        "train_number": "12951",
        "train_name": "Mumbai Rajdhani Express",
        "origin": "Mumbai Central (MMCT)",
        "destination": "New Delhi (NDLS)",
        "departure": "17:00",
        "arrival": "08:32 (+1 day)",
        "classes": {
            "1A": {"fare": 4850, "seats": 14},
            "2A": {"fare": 3050, "seats": 28},
            "3A": {"fare": 2150, "seats": 62},
        },
    },
    {
        "train_number": "12009",
        "train_name": "Mumbai - Ahmedabad Shatabdi",
        "origin": "Mumbai Central (MMCT)",
        "destination": "Ahmedabad (ADI)",
        "departure": "06:20",
        "arrival": "12:45",
        "classes": {
            "EC": {"fare": 2400, "seats": 18},
            "CC": {"fare": 1350, "seats": 44},
        },
    },
    {
        "train_number": "22436",
        "train_name": "Vande Bharat Express",
        "origin": "New Delhi (NDLS)",
        "destination": "Varanasi (BSB)",
        "departure": "06:00",
        "arrival": "14:00",
        "classes": {
            "EC": {"fare": 3300, "seats": 22},
            "CC": {"fare": 1750, "seats": 56},
        },
    },
    {
        "train_number": "12626",
        "train_name": "Kerala Express",
        "origin": "New Delhi (NDLS)",
        "destination": "Thiruvananthapuram (TVC)",
        "departure": "20:10",
        "arrival": "18:00 (+2 days)",
        "classes": {
            "2A": {"fare": 3800, "seats": 12},
            "3A": {"fare": 2550, "seats": 35},
            "SL": {"fare": 950, "seats": 80},
        },
    },
]


class MockTrainProvider(TrainProvider):
    """Safe mock railway reservation provider for local testing and demo."""

    @property
    def capability(self) -> IntegrationCapability:
        return IntegrationCapability(
            provider_name="MockTrainProvider",
            environment=ProviderEnvironment.DEMO,
            supports_search=True,
            supports_availability=True,
            supports_pricing=True,
            supports_booking=True,
            supports_cancellation=True,
            supports_refund=True,
            requires_authentication=False,
            requires_partner_access=False,
            supports_demo=True,
            notice_message="Demo simulation only. No real railway ticket was purchased.",
        )

    async def search_trains(self, origin: str, destination: str, date: str = "") -> list[dict[str, Any]]:
        return search_trains(origin, destination, date)

    async def reserve_ticket(
        self, train_number: str, passenger_name: str, travel_class: str = "3A", date: str = "", quota: str = "GN"
    ) -> dict[str, Any]:
        return book_train_ticket(train_number, passenger_name, travel_class, date)

    async def cancel_ticket(self, booking_reference: str) -> dict[str, Any]:
        return {
            "mode": "demo",
            "is_real_booking": false,
            "status": "cancelled",
            "booking_reference": booking_reference,
            "cancellation_fee": 120.0,
            "refund_amount": 4730.0,
            "message": "Demo train ticket cancelled. Simulated refund initiated.",
        }


# Singleton mock train provider
mock_train_provider = MockTrainProvider()


def search_trains(origin: str, destination: str, date: str = "") -> list[dict[str, Any]]:
    """Search available trains matching origin and destination."""
    origin_clean = origin.strip().lower()
    dest_clean = destination.strip().lower()

    matches = []
    for train in MOCK_TRAIN_CATALOG:
        orig_match = origin_clean in train["origin"].lower() or any(
            part in train["origin"].lower() for part in origin_clean.split()
        )
        dest_match = dest_clean in train["destination"].lower() or any(
            part in train["destination"].lower() for part in dest_clean.split()
        )
        if orig_match or dest_match or not (origin_clean or dest_clean):
            train_copy = dict(train)
            train_copy["mode"] = "demo"
            train_copy["is_real_booking"] = False
            matches.append(train_copy)

    if not matches:
        matches = [dict(t, mode="demo", is_real_booking=False) for t in MOCK_TRAIN_CATALOG[:2]]

    return matches


def book_train_ticket(
    train_number: str,
    passenger_name: str,
    travel_class: str = "3A",
    date: str = "",
) -> dict[str, Any]:
    """
    Reserve a train ticket.
    Strictly outputs DEMO-TRAIN-XXXX prefix and demo disclosures.
    """
    matched_train = next(
        (t for t in MOCK_TRAIN_CATALOG if t["train_number"] == train_number.strip()),
        MOCK_TRAIN_CATALOG[0],
    )

    travel_class = travel_class.upper().strip()
    class_info = matched_train["classes"].get(
        travel_class, list(matched_train["classes"].values())[0]
    )
    selected_class = travel_class if travel_class in matched_train["classes"] else list(matched_train["classes"].keys())[0]

    fare = class_info["fare"]
    # Distinct demo prefix as required by specification
    demo_ref = f"DEMO-TRAIN-{uuid.uuid4().hex[:8].upper()}"

    return {
        "mode": "demo",
        "is_real_booking": False,
        "message": "Demo booking only. No real railway ticket was purchased.",
        "provider": "MockTrainProvider",
        "pnr": demo_ref,
        "booking_reference": demo_ref,
        "train_number": matched_train["train_number"],
        "train_name": matched_train["train_name"],
        "passenger": passenger_name.strip() or "Passenger",
        "travel_class": selected_class,
        "fare": fare,
        "currency": "INR",
        "origin": matched_train["origin"],
        "destination": matched_train["destination"],
        "departure": matched_train["departure"],
        "date": date or datetime.now().strftime("%Y-%m-%d"),
        "coach": f"{selected_class}-1",
        "berth": "42 (Demo Side Lower)",
    }
