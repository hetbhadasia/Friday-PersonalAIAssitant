GIVE# F.R.I.D.A.Y. Architecture Reference

> **Guiding Principle:** EXTEND, DON'T REPLACE. PRESERVE, THEN IMPROVE.  
> F.R.I.D.A.Y. V3 introduces a transactional action subsystem while maintaining zero breaking changes to the four-process execution baseline.

---

## 1. System Overview & The Four-Process Model

F.R.I.D.A.Y. operates as four cooperating, decoupled processes:

```text
┌────────────────────────────────────────────────────────┐
│                   React 19 Frontend                    │
│             (Vite + TailwindCSS + LiveKit)             │
│               http://localhost:5173                    │
└───────────────────────────┬────────────────────────────┘
                            │ WebRTC Audio / REST API
┌───────────────────────────┴────────────────────────────┐
│                  Token & API Server                    │
│                 (FastAPI on Port 8080)                 │
│         Auth JWTs, Health Checks, Action REST API      │
└───────────────────────────┬────────────────────────────┘
                            │ REST / WebSocket
┌───────────────────────────┴────────────────────────────┐
│                   LiveKit Cloud / Local                │
│                 (WebRTC Media Gateway)                 │
└───────────────────────────┬────────────────────────────┘
                            │ WebRTC Audio Pipe
┌───────────────────────────┴────────────────────────────┐
│                    Voice Agent Worker                  │
│       (LiveKit Agents + Sarvam STT/TTS + Groq LLM)     │
└───────────────────────────┬────────────────────────────┘
                            │ SSE (Server-Sent Events)
┌───────────────────────────┴────────────────────────────┐
│                   FastMCP Tool Server                  │
│                 (FastMCP on Port 8000)                 │
│             All 30 System, Web, & Action Tools         │
└────────────────────────────────────────────────────────┘
```

### Process Definitions

1. **MCP Server** (`uv run friday` or `python server.py`):
   - FastMCP server listening on `http://127.0.0.1:8000/sse`.
   - Exposes 30 tools spanning system diagnostics, memory, tasks, web search, and transactional actions (trains, flights, movies, hotels, cancellations).

2. **Voice Agent** (`uv run friday_voice` or `uv run agent_friday.py dev`):
   - Connects to LiveKit Cloud WebRTC room.
   - Manages voice pipeline: Silero VAD → Sarvam Saaras v3 STT → Groq Llama 3.3 70B LLM → Sarvam Bulbul v3 TTS.
   - Connects to FastMCP server via SSE client to execute functions requested by the LLM.

3. **Token & REST Server** (`python token_server.py`):
   - FastAPI server listening on `http://0.0.0.0:8080`.
   - Serves LiveKit auth tokens (`/api/token`), system health metrics (`/health`, `/metrics`).
   - Serves Versioned Action APIs (`/api/v1/bookings`, `/api/v1/payments`, webhooks, checkout).

4. **React Frontend** (`cd frontend && npm run dev`):
   - Vite + React + Lucide Icons on `http://localhost:5173`.
   - Connects to LiveKit room for live voice interaction.
   - Displays real-time audio visualization, system diagnostics, and the Orders Mission Control panel.

---

## 2. Core Booking Class Diagram

The diagram below shows the main booking and payment classes, their important fields, and their relationships. It is oriented top-to-bottom for a vertical layout.

```mermaid
classDiagram
    direction TB

    class ActionOrchestrator {
        -_orders: dict~str, BookingOrder~
        +get_order(order_id) BookingOrder
        +list_orders(status, user_id) list
        +handle_train_booking(...)
        +handle_flight_booking(...)
        +handle_movie_booking(...)
        +handle_hotel_booking(...)
    }

    class OrderService {
        -_orders: dict~str, dict~
        +calculate_totals(booking_type, base_amount) dict
        +create_order_draft(...)
        +transition_state(order_id, next_state, reason)
        +advance_order_lifecycle(order_id)
        +lock_order_for_payment(order_id)
        +get_order(order_id) dict
        +list_user_orders(user_id, status) list
    }

    class BookingOrder {
        +order_id: str
        +booking_type: BookingType
        +title: str
        +description: str
        +amount: float
        +currency: str
        +status: BookingStatus
        +payment_status: PaymentStatus
        +payment_session_id: str
        +created_at: str
        +metadata: dict
        +to_dict() dict
    }

    class PaymentSession {
        +payment_id: str
        +order_id: str
        +amount: float
        +currency: str
        +status: PaymentStatus
        +checkout_url: str
        +created_at: str
        +to_dict() dict
    }

    class PaymentManager {
        +mock_provider: MockPaymentProvider
        -_active_provider: PaymentProvider
        +get_provider() PaymentProvider
    }

    class PaymentProvider {
        <<abstract>>
        +provider_name: str
        +is_real_gateway: bool
        +create_checkout_session(order_id, amount, currency, user_id) PaymentSession
        +verify_payment(payment_id) dict
        +refund_payment(payment_id, amount, reason) dict
    }

    class MockPaymentProvider {
        -_sessions: dict~str, PaymentSession~
        +create_checkout_session(...) PaymentSession
        +verify_payment(payment_id) dict
        +complete_mock_payment(payment_id) PaymentSession
        +refund_payment(payment_id, amount, reason) dict
    }

    class RazorpayProvider {
        +key_id: str
        +key_secret: str
        +create_checkout_session(...) PaymentSession
        +verify_payment(payment_id) dict
        +refund_payment(payment_id, amount, reason) dict
    }

    class CashfreeProvider {
        +app_id: str
        +secret_key: str
        +create_checkout_session(...) PaymentSession
        +verify_payment(payment_id) dict
        +refund_payment(payment_id, amount, reason) dict
    }

    class BookingState {
        <<enumeration>>
        DRAFT
        SEARCHING
        OPTION_SELECTED
        REVALIDATING
        AWAITING_USER_CONFIRMATION
        PAYMENT_REQUIRED
        PAYMENT_PENDING
        PAYMENT_VERIFIED
        BOOKING_PENDING
        CONFIRMED
        FAILED
        CANCELLED
        EXPIRED
        UNKNOWN
        RECONCILIATION_REQUIRED
    }

    class BookingType {
        <<enumeration>>
        TRAIN
        FLIGHT
        MOVIE
        HOTEL
    }

    class BookingStatus {
        <<enumeration>>
        PENDING
        CONFIRMED
        CANCELLED
        FAILED
    }

    class PaymentStatus {
        <<enumeration>>
        PENDING
        PAID
        FAILED
        CANCELLED
    }

    class TrainProvider {
        <<abstract>>
        +capability: IntegrationCapability
        +search_trains(origin, destination, date) list
        +reserve_ticket(...) dict
        +cancel_ticket(booking_reference) dict
    }

    class FlightProvider {
        <<abstract>>
        +capability: IntegrationCapability
        +search_flights(origin, destination, date) list
        +reserve_flight(...) dict
        +cancel_flight(booking_reference) dict
    }

    class MovieProvider {
        <<abstract>>
        +capability: IntegrationCapability
        +search_shows(query, city) list
        +reserve_tickets(...) dict
        +cancel_tickets(ticket_id) dict
    }

    class AccommodationProvider {
        <<abstract>>
        +capability: IntegrationCapability
        +search_accommodations(city, checkin_date) list
        +reserve_room(...) dict
        +cancel_room(booking_id) dict
    }

    class MockTrainProvider
    class MockFlightProvider
    class MockMovieProvider
    class MockAccommodationProvider

    class IntegrationCapability {
        +provider_name: str
        +environment: ProviderEnvironment
        +supports_search: bool
        +supports_booking: bool
        +supports_cancellation: bool
        +supports_refund: bool
        +notice_message: str
        +to_dict() dict
    }

    ActionOrchestrator --> OrderService : creates and advances order drafts
    ActionOrchestrator --> BookingOrder : creates and stores bookings
    ActionOrchestrator --> PaymentManager : requests checkout sessions
    ActionOrchestrator ..> TrainProvider : books trains
    ActionOrchestrator ..> FlightProvider : books flights
    ActionOrchestrator ..> MovieProvider : books movie tickets
    ActionOrchestrator ..> AccommodationProvider : books hotel stays
    OrderService --> BookingState : validates lifecycle transitions
    BookingOrder --> BookingType
    BookingOrder --> BookingStatus
    BookingOrder --> PaymentStatus
    PaymentSession --> PaymentStatus
    PaymentManager o--> PaymentProvider : selects gateway
    PaymentProvider <|.. MockPaymentProvider
    PaymentProvider <|.. RazorpayProvider
    PaymentProvider <|.. CashfreeProvider
    MockPaymentProvider --> PaymentSession : stores sessions
    TrainProvider <|.. MockTrainProvider
    FlightProvider <|.. MockFlightProvider
    MovieProvider <|.. MockMovieProvider
    AccommodationProvider <|.. MockAccommodationProvider
    TrainProvider --> IntegrationCapability
    FlightProvider --> IntegrationCapability
    MovieProvider --> IntegrationCapability
    AccommodationProvider --> IntegrationCapability
```

## 3. Universal Order Lifecycle & Finite State Machine

All bookings (trains, flights, movies, accommodations) follow a unified 15-state lifecycle enforced by `friday.actions.state_machine.OrderStateMachine`:

```mermaid
stateDiagram-v2
    [*] --> DRAFT
    DRAFT --> OPTION_SELECTED
    OPTION_SELECTED --> REVALIDATING
    REVALIDATING --> AWAITING_USER_CONFIRMATION
    AWAITING_USER_CONFIRMATION --> PAYMENT_REQUIRED
    AWAITING_USER_CONFIRMATION --> CANCELLED: User Rejects
    PAYMENT_REQUIRED --> PAYMENT_PENDING
    PAYMENT_PENDING --> PAYMENT_VERIFIED
    PAYMENT_PENDING --> PAYMENT_FAILED: Gateway Decline
    PAYMENT_VERIFIED --> BOOKING_PENDING
    BOOKING_PENDING --> CONFIRMED
    BOOKING_PENDING --> UNKNOWN: Provider Timeout
    UNKNOWN --> RECONCILIATION_REQUIRED
    UNKNOWN --> CONFIRMED: Reconciled OK
    UNKNOWN --> REFUND_PENDING: Cannot Confirm
    CONFIRMED --> CANCELLED: User Cancellation
    CONFIRMED --> REFUND_PENDING: Cancel with Refund
    REFUND_PENDING --> REFUNDED
    CANCELLED --> [*]
    REFUNDED --> [*]
    PAYMENT_FAILED --> [*]
```

### Invariants:
1. Direct transitions jumping over intermediate states (e.g., `DRAFT` directly to `CONFIRMED`) are strictly forbidden and throw `StateTransitionError`.
2. Tax and surcharge calculations are strictly performed server-side (18% GST on services).
3. Every order is assigned a unique reference ID prefixed with its type and demo status (e.g. `DEMO-TRAIN-B792A1`).

---

## 4. Directory Layout

```text
friday/
├── actions/                  # Transactional domain & providers
│   ├── interfaces.py         # Abstract provider interfaces & capabilities
│   ├── state_machine.py      # Strict 15-state order state machine
│   ├── order_service.py      # Universal order lifecycle manager
│   ├── confirmations.py      # Cryptographic SHA-256 confirmation engine
│   ├── payment_service.py    # PCI-isolated out-of-band payment gateway
│   ├── webhook.py            # HMAC-SHA256 verified payment webhooks
│   ├── reconciliation.py     # Network failure recovery & status audit
│   ├── idempotency.py        # Request deduplication engine
│   ├── cancellation.py       # Cancellation policies & refund calculation
│   ├── notifications.py      # Multi-channel notification dispatch
│   ├── railway_safety.py     # Indian Railway legal compliance validator
│   ├── trains.py             # Train search and booking provider (Demo)
│   ├── flights.py            # Flight search and booking provider (Demo)
│   ├── movies.py             # Movie search and booking provider (Demo)
│   └── hotels.py             # Hotel search and booking provider (Demo)
├── core/
│   ├── auth.py               # Bearer token auth & scoped permissions
│   ├── sanitizer.py          # Prompt-injection defense & input safety
│   ├── memory_repo.py        # Supabase/Local JSON memory storage
│   ├── task_repo.py          # Supabase/Local JSON task storage
│   └── ...
├── tools/                    # FastMCP tool registrations
│   ├── booking.py            # Search, book, and cancel action tools
│   ├── diagnostics.py        # Health and metrics tools
│   ├── memory.py             # Cognitive memory tools
│   ├── tasks.py              # Stark task management tools
│   ├── web.py                # Web search & news scraping
│   └── system.py             # System info & time tools
└── config/
    └── settings.py           # Feature flags and environment configuration
```
