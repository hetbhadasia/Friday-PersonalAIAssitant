"""
F.R.I.D.A.Y. V3 — Flight Booking Provider & Mock Implementation
===============================================================
Implements FlightProvider interface.
Strict demo isolation: References prefixed with DEMO-FLIGHT-XXXX.
"""

from typing import Any
import uuid
from datetime import datetime
from friday.actions.interfaces import FlightProvider, IntegrationCapability, ProviderEnvironment
from friday.core.logging import get_logger

logger = get_logger("action_flights")

MOCK_FLIGHT_CATALOG = [
    {
        "flight_number": "AI-806",
        "airline": "Air India",
        "origin": "Mumbai (BOM)",
        "destination": "Delhi (DEL)",
        "departure": "07:00",
        "arrival": "09:15",
        "classes": {
            "Economy": {"fare": 5400, "seats": 32},
            "Business": {"fare": 18500, "seats": 8},
        },
    },
    {
        "flight_number": "6E-205",
        "airline": "IndiGo",
        "origin": "Bengaluru (BLR)",
        "destination": "Mumbai (BOM)",
        "departure": "10:30",
        "arrival": "12:15",
        "classes": {
            "Economy": {"fare": 4200, "seats": 40},
            "FastForward": {"fare": 5600, "seats": 12},
        },
    },
    {
        "flight_number": "UK-945",
        "airline": "Vistara",
        "origin": "Delhi (DEL)",
        "destination": "Goa (GOI)",
        "departure": "14:15",
        "arrival": "16:45",
        "classes": {
            "Economy": {"fare": 6200, "seats": 24},
            "PremiumEconomy": {"fare": 9800, "seats": 10},
            "Business": {"fare": 22000, "seats": 4},
        },
    },
    {
        "flight_number": "BA-138",
        "airline": "British Airways",
        "origin": "Mumbai (BOM)",
        "destination": "London Heathrow (LHR)",
        "departure": "02:15",
        "arrival": "07:30",
        "classes": {
            "Economy": {"fare": 52000, "seats": 15},
            "ClubWorld": {"fare": 185000, "seats": 6},
        },
    },
]


class MockFlightProvider(FlightProvider):
    """Safe mock flight provider."""

    @property
    def capability(self) -> IntegrationCapability:
        return IntegrationCapability(
            provider_name="MockFlightProvider",
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
            notice_message="Demo flight simulation only. No real airline reservation was purchased.",
        )

    async def search_flights(self, origin: str, destination: str, date: str = "") -> list[dict[str, Any]]:
        return search_flights(origin, destination, date)

    async def reserve_flight(
        self, flight_number: str, passenger_name: str, seat_class: str = "Economy", date: str = ""
    ) -> dict[str, Any]:
        return book_flight_ticket(flight_number, passenger_name, seat_class, date)

    async def cancel_flight(self, booking_reference: str) -> dict[str, Any]:
        return {
            "mode": "demo",
            "is_real_booking": False,
            "status": "cancelled",
            "booking_reference": booking_reference,
            "cancellation_fee": 1500.0,
            "refund_amount": 3900.0,
            "message": "Demo flight reservation cancelled. Simulated refund initiated.",
        }


mock_flight_provider = MockFlightProvider()


def search_flights(origin: str, destination: str, date: str = "") -> list[dict[str, Any]]:
    """Search flights matching origin and destination."""
    origin_clean = origin.strip().lower()
    dest_clean = destination.strip().lower()

    matches = []
    for flight in MOCK_FLIGHT_CATALOG:
        orig_match = origin_clean in flight["origin"].lower() or any(
            part in flight["origin"].lower() for part in origin_clean.split()
        )
        dest_match = dest_clean in flight["destination"].lower() or any(
            part in flight["destination"].lower() for part in dest_clean.split()
        )
        if orig_match or dest_match or not (origin_clean or dest_clean):
            f_copy = dict(flight)
            f_copy["mode"] = "demo"
            f_copy["is_real_booking"] = False
            matches.append(f_copy)

    if not matches:
        matches = [dict(f, mode="demo", is_real_booking=False) for f in MOCK_FLIGHT_CATALOG[:2]]

    return matches


def book_flight_ticket(
    flight_number: str,
    passenger_name: str,
    seat_class: str = "Economy",
    date: str = "",
) -> dict[str, Any]:
    """Reserve a flight ticket."""
    matched = next(
        (f for f in MOCK_FLIGHT_CATALOG if f["flight_number"].lower() == flight_number.strip().lower()),
        MOCK_FLIGHT_CATALOG[0],
    )

    seat_class = seat_class.capitalize()
    class_info = matched["classes"].get(seat_class, list(matched["classes"].values())[0])
    selected_class = seat_class if seat_class in matched["classes"] else list(matched["classes"].keys())[0]

    demo_ref = f"DEMO-FLIGHT-{uuid.uuid4().hex[:8].upper()}"

    return {
        "mode": "demo",
        "is_real_booking": False,
        "message": "Demo booking only. No real airline reservation was purchased.",
        "provider": "MockFlightProvider",
        "booking_reference": demo_ref,
        "flight_number": matched["flight_number"],
        "airline": matched["airline"],
        "passenger": passenger_name.strip() or "Passenger",
        "seat_class": selected_class,
        "fare": class_info["fare"],
        "currency": "INR",
        "origin": matched["origin"],
        "destination": matched["destination"],
        "departure": matched["departure"],
        "date": date or datetime.now().strftime("%Y-%m-%d"),
        "seat": "14A (Demo Window)",
    }
