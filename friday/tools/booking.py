"""
F.R.I.D.A.Y. V2 — Transactional Action & Booking MCP Tools
==========================================================
Enables F.R.I.D.A.Y. to search and book trains, flights, movie tickets,
and luxury hotel stays with out-of-band payment orchestration.

Governed strictly by feature flag config.features.ENABLE_BOOKING.
"""

from typing import Optional
from friday.actions.orchestrator import action_orchestrator
from friday.actions.trains import search_trains
from friday.actions.flights import search_flights
from friday.actions.movies import search_movies
from friday.actions.hotels import search_hotels
from friday.config import config
from friday.core.logging import get_logger

logger = get_logger("booking_tools")


def _is_booking_enabled() -> bool:
    return getattr(config.features, "ENABLE_BOOKING", False)


def register(mcp):
    """Register all booking and reservation tools onto the FastMCP server."""

    @mcp.tool()
    async def search_train_routes(origin: str, destination: str, date: str = "") -> str:
        """
        Search available train routes and schedules between two stations/cities.
        Examples: origin='Mumbai', destination='Delhi'
        """
        if not _is_booking_enabled():
            return "Booking protocols are currently in standby mode, boss. Set ENABLE_BOOKING=true in your environment to activate train bookings."

        trains = search_trains(origin, destination, date)
        if not trains:
            return f"No direct trains found between {origin} and {destination}, boss."

        lines = [f"### Available Trains ({origin.upper()} → {destination.upper()})\n"]
        for t in trains:
            classes_str = ", ".join(
                f"{c}: ₹{info['fare']} ({info['seats']} seats)"
                for c, info in t["classes"].items()
            )
            lines.append(
                f"🚆 **{t['train_name']}** (#{t['train_number']})\n"
                f"   Dep: {t['departure']} | Arr: {t['arrival']}\n"
                f"   Classes: {classes_str}\n"
            )
        return "\n".join(lines)

    @mcp.tool()
    async def book_train(train_number: str, passenger_name: str, travel_class: str = "3A", date: str = "") -> str:
        """
        Reserve a train ticket for a passenger on a specific train.
        - train_number: The 5-digit train number (e.g. '12951')
        - passenger_name: Full name of passenger
        - travel_class: '1A', '2A', '3A', 'CC', 'EC', 'SL'
        """
        if not _is_booking_enabled():
            return "Booking protocols are currently offline, boss. Set ENABLE_BOOKING=true to enable."

        try:
            res = action_orchestrator.handle_train_booking(
                train_number=train_number,
                passenger_name=passenger_name,
                travel_class=travel_class,
                date=date,
                auto_pay=not config.features.ENABLE_REAL_PAYMENT,
            )
            details = res["details"]
            order = res["order"]
            return (
                f"✅ **Train Ticket Confirmed, Boss.**\n"
                f"- **Train**: {details['train_name']} (#{details['train_number']})\n"
                f"- **Route**: {details['origin']} → {details['destination']}\n"
                f"- **Passenger**: {details['passenger']} (Seat: {details['coach']}, Berth: {details['berth']})\n"
                f"- **PNR**: `{details['pnr']}`\n"
                f"- **Total Fare**: ₹{details['fare']} (Payment: {order['payment_status'].upper()})\n"
                f"- **Order ID**: `{order['order_id']}`"
            )
        except Exception as exc:
            logger.error("Train booking error: %s", exc)
            return f"Failed to complete train booking: {exc}"

    @mcp.tool()
    async def search_flight_routes(origin: str, destination: str, date: str = "") -> str:
        """
        Search scheduled airline flights between two cities or airport codes.
        Examples: origin='BOM', destination='DEL'
        """
        if not _is_booking_enabled():
            return "Flight booking grid is in standby mode, boss. Set ENABLE_BOOKING=true to activate."

        flights = search_flights(origin, destination, date)
        if not flights:
            return f"No scheduled flights found between {origin} and {destination}."

        lines = [f"### Available Flight Routes ({origin.upper()} → {destination.upper()})\n"]
        for f in flights:
            classes_str = ", ".join(
                f"{c}: ₹{info['fare']} ({info['seats']} seats)"
                for c, info in f["classes"].items()
            )
            lines.append(
                f"✈️ **{f['airline']}** ({f['flight_number']})\n"
                f"   Dep: {f['departure']} | Arr: {f['arrival']}\n"
                f"   Classes: {classes_str}\n"
            )
        return "\n".join(lines)

    @mcp.tool()
    async def book_flight(flight_number: str, passenger_name: str, seat_class: str = "Economy", date: str = "") -> str:
        """
        Reserve an airline flight seat for a passenger.
        - flight_number: Flight code (e.g. 'AI-806', '6E-205')
        - passenger_name: Full name of passenger
        - seat_class: 'Economy', 'PremiumEconomy', 'Business'
        """
        if not _is_booking_enabled():
            return "Flight reservations are offline, boss. Set ENABLE_BOOKING=true to enable."

        try:
            res = action_orchestrator.handle_flight_booking(
                flight_number=flight_number,
                passenger_name=passenger_name,
                seat_class=seat_class,
                date=date,
                auto_pay=not config.features.ENABLE_REAL_PAYMENT,
            )
            details = res["details"]
            order = res["order"]
            return (
                f"✅ **Flight Reservation Confirmed, Boss.**\n"
                f"- **Flight**: {details['airline']} {details['flight_number']}\n"
                f"- **Route**: {details['origin']} → {details['destination']}\n"
                f"- **Passenger**: {details['passenger']} (Seat: {details['seat']})\n"
                f"- **Booking Ref**: `{details['booking_reference']}`\n"
                f"- **Total Fare**: ₹{details['fare']} (Payment: {order['payment_status'].upper()})\n"
                f"- **Order ID**: `{order['order_id']}`"
            )
        except Exception as exc:
            logger.error("Flight booking error: %s", exc)
            return f"Failed to complete flight reservation: {exc}"

    @mcp.tool()
    async def search_movie_shows(movie_title: str = "", city: str = "") -> str:
        """
        Search currently playing movies, multiplexes, and showtimes.
        """
        if not _is_booking_enabled():
            return "Entertainment booking protocol is in standby mode. Set ENABLE_BOOKING=true to activate."

        movies = search_movies(movie_title, city)
        if not movies:
            return "No movies or theaters found matching your query, boss."

        lines = ["### Now Showing in Theaters\n"]
        for m in movies:
            lines.append(f"🎬 **{m['title']}** [{m['genre']} | {m['rating']} | {m['duration']}]")
            for c in m["cinemas"]:
                shows = ", ".join(c["showtimes"])
                lines.append(f"   🏛️ **{c['name']}** ({c['format']}) — ₹{c['ticket_price']}")
                lines.append(f"      Showtimes: {shows}")
            lines.append("")
        return "\n".join(lines)

    @mcp.tool()
    async def book_movie(movie_title: str, cinema_name: str = "", showtime: str = "", seats: int = 2) -> str:
        """
        Book movie tickets at a selected theater and showtime.
        - movie_title: Name of the movie
        - cinema_name: Multiplex or theater name
        - showtime: Desired time slot (e.g. '20:00')
        - seats: Number of tickets to book (default 2)
        """
        if not _is_booking_enabled():
            return "Cinema ticketing is currently offline. Set ENABLE_BOOKING=true to enable."

        try:
            res = action_orchestrator.handle_movie_booking(
                movie_title=movie_title,
                cinema_name=cinema_name,
                showtime=showtime,
                seats=seats,
                auto_pay=not config.features.ENABLE_REAL_PAYMENT,
            )
            details = res["details"]
            order = res["order"]
            return (
                f"🎟️ **Cinema Tickets Confirmed, Boss.**\n"
                f"- **Movie**: {details['movie_title']}\n"
                f"- **Theater**: {details['cinema']} ({details['format']})\n"
                f"- **Showtime**: {details['showtime']} on {details['date']}\n"
                f"- **Seats**: {', '.join(details['seats'])} ({details['seat_count']} tickets)\n"
                f"- **Ticket ID**: `{details['ticket_id']}`\n"
                f"- **Total Amount**: ₹{details['total_amount']} (Payment: {order['payment_status'].upper()})\n"
                f"- **Order ID**: `{order['order_id']}`"
            )
        except Exception as exc:
            logger.error("Movie booking error: %s", exc)
            return f"Failed to book movie tickets: {exc}"

    @mcp.tool()
    async def search_hotel_accommodations(city: str, checkin_date: str = "") -> str:
        """
        Search available luxury hotels, suites, and nightly rates in a city.
        """
        if not _is_booking_enabled():
            return "Hotel reservation system is in standby mode. Set ENABLE_BOOKING=true to activate."

        hotels = search_hotels(city, checkin_date)
        if not hotels:
            return f"No partner hotels found in {city}, boss."

        lines = [f"### Accommodations in {city.upper()}\n"]
        for h in hotels:
            amenities = ", ".join(h.get("amenities", []))
            lines.append(f"🏨 **{h['hotel_name']}** (Rating: {h['rating']} ⭐)")
            lines.append(f"   Amenities: {amenities}")
            for room, info in h["rooms"].items():
                lines.append(f"   • {room}: ₹{info['fare_per_night']}/night ({info['available']} available)")
            lines.append("")
        return "\n".join(lines)

    @mcp.tool()
    async def book_hotel(hotel_name: str, guest_name: str, room_type: str = "", nights: int = 1) -> str:
        """
        Book a hotel room or suite.
        - hotel_name: Name of hotel
        - guest_name: Name of primary guest
        - room_type: Room or suite category
        - nights: Number of nights stay (default 1)
        """
        if not _is_booking_enabled():
            return "Hotel reservations are currently offline. Set ENABLE_BOOKING=true to enable."

        try:
            res = action_orchestrator.handle_hotel_booking(
                hotel_name=hotel_name,
                guest_name=guest_name,
                room_type=room_type,
                nights=nights,
                auto_pay=not config.features.ENABLE_REAL_PAYMENT,
            )
            details = res["details"]
            order = res["order"]
            return (
                f"🏨 **Hotel Reservation Confirmed, Boss.**\n"
                f"- **Property**: {details['hotel_name']} ({details['city']})\n"
                f"- **Guest**: {details['guest_name']}\n"
                f"- **Room**: {details['room_type']} for {details['nights']} night(s)\n"
                f"- **Confirmation Code**: `{details['confirmation_code']}`\n"
                f"- **Total Amount**: ₹{details['total_amount']} (Payment: {order['payment_status'].upper()})\n"
                f"- **Order ID**: `{order['order_id']}`"
            )
        except Exception as exc:
            logger.error("Hotel booking error: %s", exc)
            return f"Failed to reserve hotel: {exc}"

    @mcp.tool()
    async def cancel_booking(order_id: str, reason: str = "User requested cancellation") -> str:
        """
        Cancel an existing confirmed booking and initiate refund calculation.
        - order_id: The order ID (e.g. 'ord_trn_xxxx')
        - reason: Optional cancellation reason
        """
        if not _is_booking_enabled():
            return "Cancellation protocol is in standby mode. Set ENABLE_BOOKING=true to enable."

        try:
            res = await action_orchestrator.handle_cancellation("iron-man", order_id, reason)
            pricing = res["pricing"]
            return (
                f"🛑 **Booking Cancelled Successfully, Boss.**\n"
                f"- **Order ID**: `{order_id}`\n"
                f"- **Cancellation ID**: `{res['cancellation_id']}`\n"
                f"- **Refund Amount**: ₹{pricing['estimated_refund']} (Fee: ₹{pricing['cancellation_fee']})\n"
                f"- **Status**: {res['status']}\n"
                f"- **Notice**: Simulated demo refund credited to your virtual wallet."
            )
        except Exception as exc:
            logger.error("Cancellation error for order %s: %s", order_id, exc)
            return f"Failed to cancel booking '{order_id}': {exc}"

    @mcp.tool()
    async def list_active_bookings(status: str = "all") -> str:
        """
        List all confirmed, pending, or past bookings (trains, flights, movies, hotels).
        """
        orders = action_orchestrator.list_orders(status=None if status == "all" else status)
        if not orders:
            return "No active bookings or orders found on record, boss."

        lines = [f"### F.R.I.D.A.Y. Action & Booking Log ({len(orders)} total) [DEMO MODE]\n"]
        for o in orders:
            icon = {"train": "🚆", "flight": "✈️", "movie": "🎟️", "hotel": "🏨"}.get(o["booking_type"], "📦")
            lines.append(
                f"{icon} **#{o['order_id']}** [{o['status'].upper()}] — {o['title']}\n"
                f"   ↳ {o['description']}\n"
                f"   ↳ Total: ₹{o['amount']} | Payment: {o['payment_status'].upper()} (DEMO)\n"
            )
        return "\n".join(lines)
