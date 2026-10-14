"""
F.R.I.D.A.Y. V3 — Action Orchestrator
====================================
Coordinates domain actions (Train, Flight, Movie, Hotel) and manages
lifecycle of orders, statuses, and payments.
Enforces explicit DEMO vs REAL status and integrates with OrderService.
"""

import uuid
from typing import Any, Optional
from datetime import datetime
from friday.actions.models import BookingOrder, BookingType, BookingStatus, PaymentStatus
from friday.actions.payment import create_payment_session, complete_mock_payment, get_payment_session
from friday.actions.trains import search_trains, book_train_ticket
from friday.actions.flights import search_flights, book_flight_ticket
from friday.actions.movies import search_movies, book_movie_tickets
from friday.actions.hotels import search_hotels, book_hotel_stay
from friday.actions.order_service import order_service
from friday.actions.cancellation import cancellation_service
from friday.actions.state_machine import BookingState
from friday.core.auth import AuthenticatedUser
from friday.config import config
from friday.core.logging import get_logger

logger = get_logger("action_orchestrator")


class ActionOrchestrator:
    """Singleton engine managing transactional actions and bookings."""

    def __init__(self):
        self._orders: dict[str, BookingOrder] = {}

    def get_order(self, order_id: str) -> Optional[BookingOrder]:
        return self._orders.get(order_id)

    def list_orders(self, status: Optional[str] = None, user_id: Optional[str] = None) -> list[dict[str, Any]]:
        orders = list(self._orders.values())
        if user_id:
            orders = [o for o in orders if o.metadata.get("user_id", "iron-man") == user_id]
        if status:
            orders = [o for o in orders if o.status.value.lower() == status.lower()]
        return [o.to_dict() for o in reversed(orders)]

    def handle_train_booking(
        self,
        train_number: str,
        passenger_name: str,
        travel_class: str = "3A",
        date: str = "",
        auto_pay: bool = False,
        user_id: str = "iron-man",
    ) -> dict[str, Any]:
        """Book a train ticket and register order."""
        res = book_train_ticket(train_number, passenger_name, travel_class, date)
        order_id = f"ord_trn_{uuid.uuid4().hex[:8]}"

        # Calculate authoritatively in OrderService
        draft = order_service.create_order_draft(
            user_id=user_id,
            booking_type=BookingType.TRAIN,
            title=f"Train {res['train_name']} ({res['train_number']})",
            description=f"{res['origin']} → {res['destination']} on {res['date']} for {res['passenger']} ({res['travel_class']})",
            base_amount=float(res["fare"]),
            provider_name="MockTrainProvider",
            metadata=res,
        )

        res["user_id"] = user_id
        res["order_id"] = order_id
        order = BookingOrder(
            order_id=order_id,
            booking_type=BookingType.TRAIN,
            title=draft["title"],
            description=draft["description"],
            amount=draft["total_amount"],
            currency=res.get("currency", "INR"),
            status=BookingStatus.CONFIRMED,
            metadata=res,
        )

        pay_session = create_payment_session(order_id, order.amount, order.currency)
        order.payment_session_id = pay_session.payment_id

        if auto_pay or not config.features.ENABLE_REAL_PAYMENT:
            complete_mock_payment(pay_session.payment_id)
            order.payment_status = PaymentStatus.PAID
            order_service.advance_order_lifecycle(draft["order_id"])

        self._orders[order_id] = order
        logger.info("Created train booking order: %s (Mode: %s)", order_id, res.get("mode"))
        return {"order": order.to_dict(), "details": res}

    def handle_flight_booking(
        self,
        flight_number: str,
        passenger_name: str,
        seat_class: str = "Economy",
        date: str = "",
        auto_pay: bool = False,
        user_id: str = "iron-man",
    ) -> dict[str, Any]:
        """Book a flight and register order."""
        res = book_flight_ticket(flight_number, passenger_name, seat_class, date)
        order_id = f"ord_flt_{uuid.uuid4().hex[:8]}"

        draft = order_service.create_order_draft(
            user_id=user_id,
            booking_type=BookingType.FLIGHT,
            title=f"Flight {res['airline']} ({res['flight_number']})",
            description=f"{res['origin']} → {res['destination']} on {res['date']} for {res['passenger']} ({res['seat_class']})",
            base_amount=float(res["fare"]),
            provider_name="MockFlightProvider",
            metadata=res,
        )

        res["user_id"] = user_id
        res["order_id"] = order_id
        order = BookingOrder(
            order_id=order_id,
            booking_type=BookingType.FLIGHT,
            title=draft["title"],
            description=draft["description"],
            amount=draft["total_amount"],
            currency=res.get("currency", "INR"),
            status=BookingStatus.CONFIRMED,
            metadata=res,
        )

        pay_session = create_payment_session(order_id, order.amount, order.currency)
        order.payment_session_id = pay_session.payment_id

        if auto_pay or not config.features.ENABLE_REAL_PAYMENT:
            complete_mock_payment(pay_session.payment_id)
            order.payment_status = PaymentStatus.PAID
            order_service.advance_order_lifecycle(draft["order_id"])

        self._orders[order_id] = order
        logger.info("Created flight booking order: %s", order_id)
        return {"order": order.to_dict(), "details": res}

    def handle_movie_booking(
        self,
        movie_title: str,
        cinema_name: str = "",
        showtime: str = "",
        seats: int = 2,
        auto_pay: bool = False,
        user_id: str = "iron-man",
    ) -> dict[str, Any]:
        """Book movie tickets and register order."""
        res = book_movie_tickets(movie_title, cinema_name, showtime, seats)
        order_id = f"ord_mov_{uuid.uuid4().hex[:8]}"

        draft = order_service.create_order_draft(
            user_id=user_id,
            booking_type=BookingType.MOVIE,
            title=f"Movie: {res['movie_title']}",
            description=f"{res['cinema']} at {res['showtime']} ({res['seat_count']} seats)",
            base_amount=float(res["total_amount"]),
            provider_name="MockMovieProvider",
            metadata=res,
        )

        res["user_id"] = user_id
        res["order_id"] = order_id
        order = BookingOrder(
            order_id=order_id,
            booking_type=BookingType.MOVIE,
            title=draft["title"],
            description=draft["description"],
            amount=draft["total_amount"],
            currency=res.get("currency", "INR"),
            status=BookingStatus.CONFIRMED,
            metadata=res,
        )

        pay_session = create_payment_session(order_id, order.amount, order.currency)
        order.payment_session_id = pay_session.payment_id

        if auto_pay or not config.features.ENABLE_REAL_PAYMENT:
            complete_mock_payment(pay_session.payment_id)
            order.payment_status = PaymentStatus.PAID
            order_service.advance_order_lifecycle(draft["order_id"])

        self._orders[order_id] = order
        logger.info("Created movie booking order: %s", order_id)
        return {"order": order.to_dict(), "details": res}

    def handle_hotel_booking(
        self,
        hotel_name: str,
        guest_name: str,
        room_type: str = "",
        nights: int = 1,
        auto_pay: bool = False,
        user_id: str = "iron-man",
    ) -> dict[str, Any]:
        """Book hotel stay and register order."""
        res = book_hotel_stay(hotel_name, guest_name, room_type, nights)
        order_id = f"ord_htl_{uuid.uuid4().hex[:8]}"

        draft = order_service.create_order_draft(
            user_id=user_id,
            booking_type=BookingType.HOTEL,
            title=f"Hotel: {res['hotel_name']}",
            description=f"{res['city']} for {res['guest_name']} ({res['nights']} nights)",
            base_amount=float(res["total_amount"]),
            provider_name="MockAccommodationProvider",
            metadata=res,
        )

        res["user_id"] = user_id
        res["order_id"] = order_id
        order = BookingOrder(
            order_id=order_id,
            booking_type=BookingType.HOTEL,
            title=draft["title"],
            description=draft["description"],
            amount=draft["total_amount"],
            currency=res.get("currency", "INR"),
            status=BookingStatus.CONFIRMED,
            metadata=res,
        )

        pay_session = create_payment_session(order_id, order.amount, order.currency)
        order.payment_session_id = pay_session.payment_id

        if auto_pay or not config.features.ENABLE_REAL_PAYMENT:
            complete_mock_payment(pay_session.payment_id)
            order.payment_status = PaymentStatus.PAID
            order_service.advance_order_lifecycle(draft["order_id"])

        self._orders[order_id] = order
        logger.info("Created hotel booking order: %s", order_id)
        return {"order": order.to_dict(), "details": res}

    async def handle_cancellation(self, user_id: str, order_id: str, reason: str = "") -> dict[str, Any]:
        """Cancel an existing confirmed booking and initiate refund."""
        user = AuthenticatedUser(user_id=user_id, username=user_id)
        res = await cancellation_service.request_cancellation(user, order_id, reason)
        if order_id in self._orders:
            self._orders[order_id].status = BookingStatus.CANCELLED
        return res


# Global singleton instance
action_orchestrator = ActionOrchestrator()
