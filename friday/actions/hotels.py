"""
F.R.I.D.A.Y. V3 — Hotel Booking Provider & Mock Implementation
==============================================================
Implements AccommodationProvider interface.
Strict demo isolation: References prefixed with DEMO-HOTEL-XXXX.
"""

from typing import Any
import uuid
from datetime import datetime
from friday.actions.interfaces import AccommodationProvider, IntegrationCapability, ProviderEnvironment
from friday.core.logging import get_logger

logger = get_logger("action_hotels")

MOCK_HOTEL_CATALOG = [
    {
        "hotel_name": "The Taj Mahal Palace, Mumbai",
        "city": "Mumbai",
        "rating": 5.0,
        "rooms": {
            "Luxury Grand Room": {"fare_per_night": 24000, "available": 5},
            "Tower Sea View Room": {"fare_per_night": 36000, "available": 3},
            "Presidential Suite": {"fare_per_night": 120000, "available": 1},
        },
        "amenities": ["Infinity Pool", "Jiva Spa", "Harbour View", "24/7 Butler"],
    },
    {
        "hotel_name": "ITC Maurya, A Luxury Collection Hotel",
        "city": "New Delhi",
        "rating": 4.9,
        "rooms": {
            "Executive Club Room": {"fare_per_night": 14500, "available": 8},
            "ITC One Suite": {"fare_per_night": 28000, "available": 2},
        },
        "amenities": ["Bukhara Restaurant", "Kaya Kalp Spa", "Diplomatic Security"],
    },
    {
        "hotel_name": "The Leela Palace Bengaluru",
        "city": "Bengaluru",
        "rating": 4.9,
        "rooms": {
            "Deluxe Room": {"fare_per_night": 16000, "available": 10},
            "Royal Club Suite": {"fare_per_night": 32000, "available": 4},
        },
        "amenities": ["Royal Gardens", "Citron Dining", "Helipad Access"],
    },
]


class MockAccommodationProvider(AccommodationProvider):
    """Safe mock accommodation provider."""

    @property
    def capability(self) -> IntegrationCapability:
        return IntegrationCapability(
            provider_name="MockAccommodationProvider",
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
            notice_message="Demo hotel booking simulation only. No real room reservation was made.",
        )

    async def search_accommodations(self, city: str, checkin_date: str = "") -> list[dict[str, Any]]:
        return search_hotels(city, checkin_date)

    async def reserve_room(
        self, hotel_name: str, guest_name: str, room_type: str = "", nights: int = 1
    ) -> dict[str, Any]:
        return book_hotel_stay(hotel_name, guest_name, room_type, nights)

    async def cancel_room(self, booking_id: str) -> dict[str, Any]:
        return {
            "mode": "demo",
            "is_real_booking": False,
            "status": "cancelled",
            "booking_id": booking_id,
            "cancellation_fee": 0.0,
            "refund_amount": 24000.0,
            "message": "Demo hotel reservation cancelled. Simulated refund initiated.",
        }


mock_accommodation_provider = MockAccommodationProvider()


def search_hotels(city: str, checkin_date: str = "", checkout_date: str = "") -> list[dict[str, Any]]:
    """Search available luxury hotels in a city."""
    city_clean = city.strip().lower()

    matches = [
        h for h in MOCK_HOTEL_CATALOG
        if not city_clean or city_clean in h["city"].lower() or city_clean in h["hotel_name"].lower()
    ]

    results = []
    for h in (matches or MOCK_HOTEL_CATALOG[:2]):
        h_copy = dict(h)
        h_copy["mode"] = "demo"
        h_copy["is_real_booking"] = False
        results.append(h_copy)

    return results


def book_hotel_stay(
    hotel_name: str,
    guest_name: str,
    room_type: str = "",
    nights: int = 1,
) -> dict[str, Any]:
    """Reserve a hotel room."""
    matched_hotel = next(
        (h for h in MOCK_HOTEL_CATALOG if hotel_name.strip().lower() in h["hotel_name"].lower()),
        MOCK_HOTEL_CATALOG[0],
    )

    rooms = matched_hotel["rooms"]
    matched_room_key = next(
        (r for r in rooms if room_type.strip().lower() in r.lower()),
        list(rooms.keys())[0],
    )
    room_data = rooms[matched_room_key]

    nights = max(1, min(nights, 30))
    total_fare = room_data["fare_per_night"] * nights
    demo_ref = f"DEMO-HOTEL-{uuid.uuid4().hex[:8].upper()}"

    return {
        "mode": "demo",
        "is_real_booking": False,
        "message": "Demo booking only. No real room reservation was purchased.",
        "provider": "MockAccommodationProvider",
        "booking_id": demo_ref,
        "booking_reference": demo_ref,
        "hotel_name": matched_hotel["hotel_name"],
        "city": matched_hotel["city"],
        "guest_name": guest_name.strip() or "Guest",
        "room_type": matched_room_key,
        "nights": nights,
        "rate_per_night": room_data["fare_per_night"],
        "total_amount": total_fare,
        "currency": "INR",
        "checkin_date": datetime.now().strftime("%Y-%m-%d"),
        "confirmation_code": f"DEMO-CONF-{uuid.uuid4().int % 1000000:06d}",
    }
