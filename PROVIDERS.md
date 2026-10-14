# F.R.I.D.A.Y. Provider Registry & Integration Matrix

## 1. Provider Interface Contracts

All service integrations implement canonical abstract base classes defined in `friday.actions.interfaces`:

- `TrainProvider`: `search_trains()`, `get_train_fare()`, `reserve_train_seats()`
- `FlightProvider`: `search_flights()`, `get_flight_fare()`, `book_flight_ticket()`
- `MovieProvider`: `search_movies()`, `get_showtimes()`, `reserve_movie_seats()`
- `AccommodationProvider`: `search_hotels()`, `get_room_rates()`, `book_hotel_room()`
- `PaymentProvider`: `create_checkout_session()`, `verify_payment_signature()`, `refund_payment()`

---

## 2. Capabilities Matrix

| Provider Class | Domain | Default Active | Capabilities | Fallback |
|:---|:---|:---:|:---|:---|
| `MockTrainProvider` | Trains | **Yes** | Search, Availability, PNR Simulation | Synthetic schedule |
| `MockFlightProvider` | Flights | **Yes** | Airline search, Fare tier, Seat allocation | Synthetic routes |
| `MockMovieProvider` | Movies | **Yes** | Showtimes, Seat selection, Hall mapping | Synthetic shows |
| `MockHotelProvider` | Hotels | **Yes** | City hotels, Room categories, Stay nights | Synthetic inventory |
| `MockPaymentProvider` | Payments | **Yes** | Out-of-band checkout URL, instant simulation | Auto-verify |
| `RazorpayProvider` | Payments | No | Standard Checkout, Webhook HMAC, Refunds | Requires API Key |
| `CashfreeProvider` | Payments | No | PG Payment Session, Webhook HMAC, Refunds | Requires App ID |

---

## 3. Production Readiness & Configuration

To enable real-world third-party providers:

1. Obtain merchant accounts and API credentials.
2. In `.env`, set:
   ```env
   ENABLE_BOOKING=true
   ENABLE_REAL_BOOKING=true
   ENABLE_REAL_PAYMENT=true
   
   # Payment Gateway Keys
   RAZORPAY_KEY_ID=rzp_live_xxxxxxxx
   RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxx
   PAYMENT_WEBHOOK_SECRET=xxxxxxxxxxxxxxxx
   ```
3. When `ENABLE_REAL_BOOKING=false` or `ENABLE_REAL_PAYMENT=false`, all actions run safely inside the Mock Sandbox without charging money or contacting external transit authorities.
