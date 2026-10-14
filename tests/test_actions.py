"""
Unit Tests for F.R.I.D.A.Y. V2 — Actions & Booking Subsystem
============================================================
"""

import unittest
from friday.actions.trains import search_trains, book_train_ticket
from friday.actions.flights import search_flights, book_flight_ticket
from friday.actions.movies import search_movies, book_movie_tickets
from friday.actions.hotels import search_hotels, book_hotel_stay
from friday.actions.payment import create_payment_session, complete_mock_payment, get_payment_session
from friday.actions.orchestrator import action_orchestrator
from friday.actions.models import BookingStatus, PaymentStatus


class TestFridayActions(unittest.TestCase):

    def test_train_search_and_booking(self):
        trains = search_trains("Mumbai", "Delhi")
        self.assertGreater(len(trains), 0)
        t = trains[0]
        self.assertIn("train_number", t)

        res = book_train_ticket(t["train_number"], "Tony Stark", "1A")
        self.assertTrue(res["pnr"].startswith(("IR", "DEMO-TRAIN-")))
        self.assertEqual(res["passenger"], "Tony Stark")
        self.assertEqual(res["currency"], "INR")

    def test_flight_search_and_booking(self):
        flights = search_flights("Mumbai", "Delhi")
        self.assertGreater(len(flights), 0)
        f = flights[0]
        self.assertIn("flight_number", f)

        res = book_flight_ticket(f["flight_number"], "Tony Stark", "Business")
        self.assertTrue(res["booking_reference"].startswith(("FL-", "DEMO-FLIGHT-")))
        self.assertEqual(res["passenger"], "Tony Stark")

    def test_movie_search_and_booking(self):
        movies = search_movies("Avengers", "Mumbai")
        self.assertGreater(len(movies), 0)
        m = movies[0]
        self.assertIn("title", m)

        res = book_movie_tickets(m["title"], seat_count=3)
        self.assertTrue(res["ticket_id"].startswith(("TIX-", "DEMO-MOVIE-")))
        self.assertEqual(res["seat_count"], 3)
        self.assertEqual(len(res["seats"]), 3)

    def test_hotel_search_and_booking(self):
        hotels = search_hotels("Mumbai")
        self.assertGreater(len(hotels), 0)
        h = hotels[0]
        self.assertIn("hotel_name", h)

        res = book_hotel_stay(h["hotel_name"], "Pepper Potts", nights=2)
        self.assertTrue(res["booking_id"].startswith(("HTL-", "DEMO-HOTEL-")))
        self.assertEqual(res["nights"], 2)

    def test_payment_session_lifecycle(self):
        session = create_payment_session("ord_test_123", 4500.0, "INR")
        self.assertEqual(session.status, PaymentStatus.PENDING)
        self.assertIn("8080/api/v1/payments", session.checkout_url)

        retrieved = get_payment_session(session.payment_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.amount, 4500.0)

        paid = complete_mock_payment(session.payment_id)
        self.assertEqual(paid.status, PaymentStatus.PAID)

    def test_action_orchestrator(self):
        result = action_orchestrator.handle_train_booking(
            train_number="12951",
            passenger_name="Tony Stark",
            travel_class="1A",
            auto_pay=True,
        )
        self.assertIn("order", result)
        order = result["order"]
        self.assertEqual(order["status"], BookingStatus.CONFIRMED.value)
        self.assertEqual(order["payment_status"], PaymentStatus.PAID.value)

        # Check in orders list
        all_orders = action_orchestrator.list_orders()
        self.assertGreater(len(all_orders), 0)


if __name__ == "__main__":
    unittest.main()
