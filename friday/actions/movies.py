"""
F.R.I.D.A.Y. V3 — Movie Ticket Booking Provider & Mock Implementation
====================================================================
Implements MovieProvider interface.
Strict demo isolation: References prefixed with DEMO-MOVIE-XXXX.
"""

from typing import Any
import uuid
from datetime import datetime
from friday.actions.interfaces import MovieProvider, IntegrationCapability, ProviderEnvironment
from friday.core.logging import get_logger

logger = get_logger("action_movies")

MOCK_MOVIE_CATALOG = [
    {
        "title": "Avengers: Secret Wars",
        "genre": "Sci-Fi / Action",
        "rating": "PG-13",
        "duration": "165 mins",
        "cinemas": [
            {
                "name": "PVR ICON Palladium, Mumbai",
                "format": "IMAX 3D Laser",
                "showtimes": ["13:00", "16:30", "20:00", "23:15"],
                "ticket_price": 650,
            },
            {
                "name": "INOX Megaplex, Inorbit Malad",
                "format": "Insignia ScreenX",
                "showtimes": ["14:15", "18:00", "21:30"],
                "ticket_price": 550,
            },
        ],
    },
    {
        "title": "Iron Man: Extremis Legacy",
        "genre": "Sci-Fi / Drama",
        "rating": "PG-13",
        "duration": "140 mins",
        "cinemas": [
            {
                "name": "PVR Directors Cut, Delhi",
                "format": "Gold Class Dolby Atmos",
                "showtimes": ["15:00", "19:00", "22:00"],
                "ticket_price": 900,
            },
            {
                "name": "Cinepolis Forum, Bengaluru",
                "format": "4DX with Motion",
                "showtimes": ["12:30", "16:00", "19:30"],
                "ticket_price": 480,
            },
        ],
    },
    {
        "title": "Oppenheimer (Special 70mm Screen)",
        "genre": "Biography / History",
        "rating": "R",
        "duration": "180 mins",
        "cinemas": [
            {
                "name": "Prasads Multiplex, Hyderabad",
                "format": "70mm IMAX Large Format",
                "showtimes": ["11:00", "15:00", "19:00"],
                "ticket_price": 400,
            },
        ],
    },
]


class MockMovieProvider(MovieProvider):
    """Safe mock cinema provider."""

    @property
    def capability(self) -> IntegrationCapability:
        return IntegrationCapability(
            provider_name="MockMovieProvider",
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
            notice_message="Demo cinema ticketing simulation only. No real tickets were purchased.",
        )

    async def search_shows(self, query: str = "", city: str = "") -> list[dict[str, Any]]:
        return search_movies(query, city)

    async def reserve_tickets(
        self, movie_title: str, cinema_name: str = "", showtime: str = "", seat_count: int = 2
    ) -> dict[str, Any]:
        return book_movie_tickets(movie_title, cinema_name, showtime, seat_count)

    async def cancel_tickets(self, ticket_id: str) -> dict[str, Any]:
        return {
            "mode": "demo",
            "is_real_booking": False,
            "status": "cancelled",
            "ticket_id": ticket_id,
            "cancellation_fee": 50.0,
            "refund_amount": 1250.0,
            "message": "Demo cinema booking cancelled. Simulated refund initiated.",
        }


mock_movie_provider = MockMovieProvider()


def search_movies(query: str = "", city: str = "") -> list[dict[str, Any]]:
    """Search currently playing films and theaters."""
    q_clean = query.strip().lower()
    city_clean = city.strip().lower()

    matches = []
    for movie in MOCK_MOVIE_CATALOG:
        title_match = not q_clean or q_clean in movie["title"].lower() or any(
            part in movie["title"].lower() for part in q_clean.split()
        )
        if not title_match:
            continue

        matched_cinemas = [
            c for c in movie["cinemas"]
            if not city_clean or city_clean in c["name"].lower()
        ]

        if matched_cinemas or not city_clean:
            movie_copy = dict(movie)
            movie_copy["mode"] = "demo"
            movie_copy["is_real_booking"] = False
            movie_copy["cinemas"] = matched_cinemas or movie["cinemas"]
            matches.append(movie_copy)

    if not matches:
        matches = [dict(m, mode="demo", is_real_booking=False) for m in MOCK_MOVIE_CATALOG[:2]]

    return matches


def book_movie_tickets(
    movie_title: str,
    cinema_name: str = "",
    showtime: str = "",
    seat_count: int = 2,
) -> dict[str, Any]:
    """Reserve movie tickets."""
    matched_movie = next(
        (m for m in MOCK_MOVIE_CATALOG if movie_title.strip().lower() in m["title"].lower()),
        MOCK_MOVIE_CATALOG[0],
    )

    cinemas = matched_movie["cinemas"]
    matched_cinema = next(
        (c for c in cinemas if cinema_name.strip().lower() in c["name"].lower()),
        cinemas[0],
    )

    chosen_showtime = showtime.strip() if showtime else matched_cinema["showtimes"][0]
    seat_count = max(1, min(seat_count, 10))
    total_price = matched_cinema["ticket_price"] * seat_count
    demo_ref = f"DEMO-MOVIE-{uuid.uuid4().hex[:8].upper()}"

    seats = [f"G{10 + i}" for i in range(seat_count)]

    return {
        "mode": "demo",
        "is_real_booking": False,
        "message": "Demo booking only. No real cinema admission ticket was purchased.",
        "provider": "MockMovieProvider",
        "ticket_id": demo_ref,
        "booking_reference": demo_ref,
        "movie_title": matched_movie["title"],
        "cinema": matched_cinema["name"],
        "format": matched_cinema["format"],
        "showtime": chosen_showtime,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "seats": seats,
        "seat_count": seat_count,
        "price_per_ticket": matched_cinema["ticket_price"],
        "total_amount": total_price,
        "currency": "INR",
    }
