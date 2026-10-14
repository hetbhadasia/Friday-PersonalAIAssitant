# F.R.I.D.A.Y. Payments & Voice PCI Isolation

## 1. Strict Voice PCI-DSS Isolation Architecture

**Cardinal Security Rule:**
> Card numbers, CVVs, expiration dates, UPI PINs, net banking passwords, and OTPs **MUST NEVER** enter the voice audio stream, STT transcripts, LLM prompt context, or MCP tool parameters.

```text
User Spoken Voice
       │
       ▼
Voice Agent (LiveKit + Groq)
       │
       │ Spoken: "Please proceed with payment for order #1234"
       ▼
Out-of-Band Payment Link Generation (FastMCP / Token Server)
       │
       ▼
Hosted Checkout Session URL (http://localhost:8080/api/v1/payments/{id}/checkout)
       │
       ▼
User completes payment securely on out-of-band payment gateway (Razorpay / Cashfree / Mock)
       │
       ▼
Signed Webhook Callback (HMAC-SHA256 verified)
       │
       ▼
Order State Transition -> PAYMENT_VERIFIED -> BOOKING_PENDING -> CONFIRMED
       │
       ▼
Voice Agent announces: "Payment verified. Your booking is confirmed."
```

---

## 2. Payment Providers

The payment layer (`friday.actions.payment_service`) abstracts payment processors via `PaymentProvider`:

1. **`MockPaymentProvider` (Default):**
   - Active when `ENABLE_REAL_PAYMENT=false`.
   - Generates mock session URLs: `/api/v1/payments/{payment_id}/checkout`.
   - Provides instant simulation completion endpoints for automated UI testing.

2. **`RazorpayProvider` (Production Ready):**
   - Activated via `ENABLE_REAL_PAYMENT=true` and `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`.
   - Generates official Razorpay Standard Checkout orders.

3. **`CashfreeProvider` (Production Ready):**
   - Activated via `ENABLE_REAL_PAYMENT=true` and `CASHFREE_APP_ID`, `CASHFREE_SECRET_KEY`.
   - Generates official Cashfree PG payment sessions.

---

## 3. Webhook Security & Tamper Protection

All incoming webhooks handled at `/api/v1/payments/webhook` are processed by `friday.actions.webhook.WebhookVerifier`:

- **HMAC-SHA256 Signature Verification:** Validates `X-Razorpay-Signature` or `X-Cashfree-Signature` against `PAYMENT_WEBHOOK_SECRET`.
- **Replay Protection:** Rejects payloads with timestamp drift greater than 300 seconds (5 minutes).
- **Idempotency Store:** Every webhook event ID (`event_id`) is cached in `IdempotencyService` to prevent duplicate processing.
