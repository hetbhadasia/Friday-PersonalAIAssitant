# F.R.I.D.A.Y. Booking Engine Reference

## 1. Domain Coverage

F.R.I.D.A.Y. supports four key consumer service domains:

| Domain | Provider Contract | MCP Search Tool | MCP Booking Tool | Mock Reference Format |
|:---|:---|:---|:---|:---|
| **Trains** | `TrainProvider` | `search_trains` | `book_train` | `DEMO-TRAIN-XXXX` |
| **Flights** | `FlightProvider` | `search_flights` | `book_flight` | `DEMO-FLIGHT-XXXX` |
| **Movies** | `MovieProvider` | `search_movies` | `book_movie` | `DEMO-MOVIE-XXXX` |
| **Hotels** | `AccommodationProvider` | `search_hotels` | `book_hotel` | `DEMO-HOTEL-XXXX` |

---

## 2. Demo vs. Real Isolation

To ensure complete safety and prevent unintended real-world financial liability or API abuse:

1. **Default Mode:** All transactions run in **DEMO SIMULATION** mode.
2. **Explicit Metadata:** Every mock search result and booking result contains:
   ```json
   {
     "mode": "demo",
     "is_real_booking": false
   }
   ```
3. **Reference Identification:** Demo booking confirmation codes strictly use the prefixes `DEMO-TRAIN-`, `DEMO-FLIGHT-`, `DEMO-MOVIE-`, and `DEMO-HOTEL-`.
4. **Safety Guards:** Production actions require `ENABLE_REAL_BOOKING=true` and `ENABLE_REAL_PAYMENT=true` in `.env`, along with valid authorized credentials.

---

## 3. The 15-State Finite State Machine

Orders must transition sequentially through the following states defined in `OrderState`:

1. `DRAFT`: Initial order creation with passenger/itinerary details.
2. `OPTION_SELECTED`: Specific class/seat/room tier assigned.
3. `REVALIDATING`: Fare and seat availability checked against live/mock provider.
4. `AWAITING_USER_CONFIRMATION`: User confirmation token issued with cryptographic hash.
5. `PAYMENT_REQUIRED`: Order locked; payment gateway checkout session initiated.
6. `PAYMENT_PENDING`: Customer redirected to out-of-band checkout page.
7. `PAYMENT_VERIFIED`: Webhook HMAC verified; payment confirmed received.
8. `BOOKING_PENDING`: Reservation request dispatched to downstream booking provider.
9. `CONFIRMED`: Ticket/PNR issued; reference code assigned; notification sent.
10. `PAYMENT_FAILED`: Gateway rejected payment; order terminal.
11. `UNKNOWN`: Booking provider timed out or dropped connection after payment.
12. `RECONCILIATION_REQUIRED`: Order queued for background polling/provider reconciliation.
13. `CANCELLATION_PENDING`: Cancellation requested; calculating cancellation fee.
14. `CANCELLED`: Order cancelled successfully.
15. `REFUND_PENDING` / `REFUNDED`: Refund processed back through payment gateway.

---

## 4. MCP Tools & Voice Integration

Users can interact naturally via voice:

- *"Friday, search trains from New Delhi to Mumbai for tomorrow."*
  → Agent calls `search_trains(origin="NDLS", destination="MMCT", travel_date="2026-10-04")`.
- *"Book 2 tickets on the Rajdhani Express for Tony Stark."*
  → Agent calls `book_train(train_number="12952", passenger_name="Tony Stark", travel_class="3A", passengers=2)`.
- *"Cancel order ord_tra_011695d9."*
  → Agent calls `cancel_booking(order_id="ord_tra_011695d9", reason="Change of plans")`.
