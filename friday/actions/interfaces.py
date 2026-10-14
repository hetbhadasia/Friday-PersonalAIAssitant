"""
F.R.I.D.A.Y. V3 — Provider Abstraction & Capability Specification
==================================================================
Strict separation between abstract provider contracts and mock/real implementations.
Explicitly flags DEMO vs REAL provider capabilities.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ProviderEnvironment(str, Enum):
    DEMO = "demo"
    SANDBOX = "sandbox"
    PRODUCTION = "production"


@dataclass(frozen=True)
class IntegrationCapability:
    """Declares the exact capabilities supported by an integration."""
    provider_name: str
    environment: ProviderEnvironment
    supports_search: bool = True
    supports_availability: bool = True
    supports_pricing: bool = True
    supports_booking: bool = True
    supports_cancellation: bool = True
    supports_refund: bool = True
    supports_modification: bool = False
    requires_authentication: bool = False
    requires_partner_access: bool = False
    supports_demo: bool = True
    notice_message: str = "Demo simulation only. No real reservation is made."

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "environment": self.environment.value,
            "supports_search": self.supports_search,
            "supports_availability": self.supports_availability,
            "supports_pricing": self.supports_pricing,
            "supports_booking": self.supports_booking,
            "supports_cancellation": self.supports_cancellation,
            "supports_refund": self.supports_refund,
            "supports_modification": self.supports_modification,
            "requires_authentication": self.requires_authentication,
            "requires_partner_access": self.requires_partner_access,
            "supports_demo": self.supports_demo,
            "notice_message": self.notice_message,
        }


class TrainProvider(ABC):
    """Abstract interface for railway reservation systems."""

    @property
    @abstractmethod
    def capability(self) -> IntegrationCapability:
        pass

    @abstractmethod
    async def search_trains(self, origin: str, destination: str, date: str) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def reserve_ticket(
        self, train_number: str, passenger_name: str, travel_class: str, date: str, quota: str = "GN"
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    async def cancel_ticket(self, booking_reference: str) -> dict[str, Any]:
        pass


class FlightProvider(ABC):
    """Abstract interface for airline reservation systems."""

    @property
    @abstractmethod
    def capability(self) -> IntegrationCapability:
        pass

    @abstractmethod
    async def search_flights(self, origin: str, destination: str, date: str) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def reserve_flight(
        self, flight_number: str, passenger_name: str, seat_class: str, date: str
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    async def cancel_flight(self, booking_reference: str) -> dict[str, Any]:
        pass


class MovieProvider(ABC):
    """Abstract interface for cinema ticketing systems."""

    @property
    @abstractmethod
    def capability(self) -> IntegrationCapability:
        pass

    @abstractmethod
    async def search_shows(self, query: str, city: str) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def reserve_tickets(
        self, movie_title: str, cinema_name: str, showtime: str, seat_count: int
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    async def cancel_tickets(self, ticket_id: str) -> dict[str, Any]:
        pass


class AccommodationProvider(ABC):
    """Abstract interface for hotel & suite booking systems."""

    @property
    @abstractmethod
    def capability(self) -> IntegrationCapability:
        pass

    @abstractmethod
    async def search_accommodations(self, city: str, checkin_date: str) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def reserve_room(
        self, hotel_name: str, guest_name: str, room_type: str, nights: int
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    async def cancel_room(self, booking_id: str) -> dict[str, Any]:
        pass
