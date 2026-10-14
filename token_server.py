"""
F.R.I.D.A.Y. V2 — Secure Token & Health Server
===============================================
aiohttp server providing:
- LiveKit token generation with input validation
- Strict CORS & origin control
- Sliding window rate limiting
- Health checks (/health, /health/live, /health/ready)
- Metrics telemetry (/metrics)
"""

import os
import re
import time
from collections import defaultdict
from aiohttp import web
from livekit.api import AccessToken, VideoGrants

from friday.config import config
from friday.core.logging import get_logger, setup_logging
from friday.core.health import health_checker
from friday.core.metrics import metrics

logger = get_logger("token_server")

routes = web.RouteTableDef()

# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Sliding-window IP rate limiter."""
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        # Clean expired timestamps
        self.requests[client_ip] = [t for t in self.requests[client_ip] if t > cutoff]
        if len(self.requests[client_ip]) >= self.max_requests:
            return False
        self.requests[client_ip].append(now)
        return True


rate_limiter = RateLimiter(
    max_requests=config.security.RATE_LIMIT_REQUESTS,
    window_seconds=config.security.RATE_LIMIT_WINDOW_SECONDS,
)

# ---------------------------------------------------------------------------
# CORS Helpers
# ---------------------------------------------------------------------------

def get_cors_headers(request: web.Request) -> dict[str, str]:
    origin = request.headers.get("Origin", "")
    allowed = config.security.ALLOWED_ORIGINS

    # If in development or origin in allowed list
    if config.env.is_development or not allowed or "*" in allowed or origin in allowed:
        allow_origin = origin if origin else "*"
    else:
        allow_origin = allowed[0] if allowed else "http://localhost:5173"

    return {
        "Access-Control-Allow-Origin": allow_origin,
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Max-Age": "86400",
    }


def sanitize_string(value: str, max_length: int = 64) -> str:
    """Sanitize room name or identity."""
    cleaned = re.sub(r'[^a-zA-Z0-9_\-\.]', '', value.strip())
    return cleaned[:max_length]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@routes.get("/health")
async def health_endpoint(request: web.Request):
    """Full health report endpoint."""
    report = health_checker.check_all()
    status_code = 200 if report.status in ("healthy", "degraded") else 503
    return web.json_response(report.to_dict(), status=status_code, headers=get_cors_headers(request))


@routes.get("/health/live")
async def liveness_endpoint(request: web.Request):
    """Liveness probe."""
    return web.json_response(health_checker.check_liveness(), status=200, headers=get_cors_headers(request))


@routes.get("/health/ready")
async def readiness_endpoint(request: web.Request):
    """Readiness probe."""
    ready_info = health_checker.check_readiness()
    status_code = 200 if ready_info.get("ready") else 503
    return web.json_response(ready_info, status=status_code, headers=get_cors_headers(request))


@routes.get("/metrics")
async def metrics_endpoint(request: web.Request):
    """Application metrics."""
    return web.json_response(metrics.get_summary(), headers=get_cors_headers(request))


@routes.get("/api/config")
async def public_config_endpoint(request: web.Request):
    """Safe public configuration for UI clients."""
    return web.json_response({
        "server_name": config.server.SERVER_NAME,
        "default_room": config.livekit.DEFAULT_ROOM,
        "environment": config.env.APP_ENV,
        "features": {
            "web_search": config.features.ENABLE_WEB_SEARCH,
            "memory": config.features.ENABLE_MEMORY,
            "tasks": config.features.ENABLE_TASKS,
            "database": config.features.ENABLE_DATABASE,
        }
    }, headers=get_cors_headers(request))


@routes.options("/api/token")
@routes.options("/health")
@routes.options("/metrics")
@routes.options("/api/config")
@routes.options("/api/v1/bookings")
@routes.options(r"/api/v1/bookings/{order_id}/cancel")
@routes.options("/api/v1/payments")
@routes.options("/api/v1/payments/webhook")
@routes.options(r"/api/v1/payments/{payment_id}/checkout")
@routes.options(r"/api/v1/payments/{payment_id}/complete")
async def options_handler(request: web.Request):
    """CORS Preflight."""
    return web.Response(status=200, headers=get_cors_headers(request))


# ---------------------------------------------------------------------------
# Versioned Action & Booking Endpoints (/api/v1/...)
# ---------------------------------------------------------------------------

@routes.get("/api/v1/bookings")
async def list_bookings_endpoint(request: web.Request):
    """List action orders and bookings isolated by user."""
    from friday.actions.orchestrator import action_orchestrator
    auth_header = request.headers.get("Authorization", "")
    user_id = "iron-man"
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        from friday.core.auth import security_token_manager
        user = security_token_manager.verify_user_token(token)
        if user:
            user_id = user.user_id

    status = request.query.get("status")
    orders = action_orchestrator.list_orders(status=status, user_id=user_id)
    return web.json_response({
        "count": len(orders),
        "user_id": user_id,
        "mode": "demo" if not getattr(config.features, "ENABLE_REAL_BOOKING", False) else "production",
        "orders": orders,
    }, headers=get_cors_headers(request))


@routes.post(r"/api/v1/bookings/{order_id}/cancel")
async def cancel_booking_endpoint(request: web.Request):
    """Cancel a confirmed booking with refund calculation."""
    from friday.actions.orchestrator import action_orchestrator
    order_id = request.match_info.get("order_id", "")
    try:
        data = await request.json() if request.can_read_body else {}
    except Exception:
        data = {}
    reason = data.get("reason", "Cancelled via API")

    try:
        res = await action_orchestrator.handle_cancellation("iron-man", order_id, reason)
        return web.json_response({"status": "success", "cancellation": res}, headers=get_cors_headers(request))
    except Exception as exc:
        return web.json_response({"error": str(exc)}, status=400, headers=get_cors_headers(request))


@routes.get("/api/v1/payments")
async def list_payments_endpoint(request: web.Request):
    """List payment sessions."""
    from friday.actions.payment import list_payment_sessions
    sessions = list_payment_sessions()
    return web.json_response({
        "count": len(sessions),
        "sessions": sessions,
    }, headers=get_cors_headers(request))


@routes.post("/api/v1/payments/webhook")
async def payment_webhook_endpoint(request: web.Request):
    """Secure gateway webhook endpoint with signature and replay verification."""
    from friday.actions.webhook import process_payment_webhook
    from friday.actions.payment import complete_mock_payment
    from friday.actions.order_service import order_service
    from friday.actions.state_machine import BookingState

    signature = request.headers.get("X-Gateway-Signature", "")
    body_bytes = await request.read()

    try:
        payload = await request.json()
    except Exception:
        return web.json_response({"error": "Malformed JSON body"}, status=400, headers=get_cors_headers(request))

    valid, reason, details = process_payment_webhook(payload, body_bytes, signature, secret=getattr(config.security, "AUTH_SECRET", ""))
    if not valid:
        return web.json_response({"error": reason}, status=401, headers=get_cors_headers(request))

    if not details.get("duplicate"):
        order_id = details["order_id"]
        payment_id = details["payment_id"]
        status = details["status"]
        if status.lower() in ("paid", "success", "captured"):
            try:
                complete_mock_payment(payment_id)
                order_service.transition_state(order_id, BookingState.PAYMENT_VERIFIED, "Webhook payment verification")
            except Exception as e:
                logger.error("Error executing state transition on webhook: %s", e)

    return web.json_response({"status": "acknowledged", "details": details}, headers=get_cors_headers(request))


@routes.post(r"/api/v1/payments/{payment_id}/complete")
async def complete_payment_endpoint(request: web.Request):
    """Out-of-band mock payment completion webhook / callback."""
    from friday.actions.payment import complete_mock_payment, get_payment_session
    payment_id = request.match_info.get("payment_id", "")
    session = complete_mock_payment(payment_id)
    if not session:
        return web.json_response({"error": "Payment session not found"}, status=404, headers=get_cors_headers(request))
    return web.json_response({"status": "success", "session": session.to_dict()}, headers=get_cors_headers(request))


@routes.get(r"/api/v1/payments/{payment_id}/checkout")
async def checkout_html_endpoint(request: web.Request):
    """Hosted out-of-band checkout landing page."""
    from friday.actions.payment import get_payment_session
    payment_id = request.match_info.get("payment_id", "")
    session = get_payment_session(payment_id)
    if not session:
        return web.Response(text="Payment Session Expired or Invalid", status=404)
    
    html = f"""<!DOCTYPE html>
<html>
<head><title>F.R.I.D.A.Y. Secure Checkout</title>
<style>
body {{ background: #0B0E14; color: #E0E6ED; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
.card {{ background: #161B22; border: 1px solid #00F0FF; border-radius: 12px; padding: 2rem; width: 380px; text-align: center; box-shadow: 0 0 20px rgba(0,240,255,0.2); }}
h2 {{ color: #00F0FF; margin-top: 0; }}
.btn {{ background: #00F0FF; color: #000; font-weight: bold; border: none; padding: 0.75rem 1.5rem; border-radius: 6px; cursor: pointer; margin-top: 1rem; }}
</style>
</head>
<body>
<div class="card">
  <h2>F.R.I.D.A.Y. Secure Checkout</h2>
  <p>Order Reference: <strong>{session.order_id}</strong></p>
  <p>Amount to Authorize: <strong>₹{session.amount} {session.currency}</strong></p>
  <p style="font-size:0.8rem;color:#8B949E;">Out-of-band secure payment gateway. No credentials touched by LLM.</p>
  <form method="POST" action="/api/v1/payments/{payment_id}/complete">
    <button class="btn" type="submit">Authorize Payment</button>
  </form>
</div>
</body>
</html>"""
    return web.Response(text=html, content_type="text/html", headers=get_cors_headers(request))


@routes.get("/api/token")
async def get_token(request: web.Request):
    """Generate LiveKit connection token."""
    client_ip = request.remote or "unknown"
    if config.features.ENABLE_RATE_LIMITING and not rate_limiter.is_allowed(client_ip):
        logger.warning("Rate limit exceeded for IP: %s", client_ip)
        return web.json_response(
            {"error": "Too many requests. Please slow down, boss."},
            status=429,
            headers=get_cors_headers(request),
        )

    raw_room = request.query.get("room_name", config.livekit.DEFAULT_ROOM)
    raw_identity = request.query.get("identity", "iron-man")

    room_name = sanitize_string(raw_room, config.security.MAX_ROOM_NAME_LENGTH) or "friday-lab"
    identity = sanitize_string(raw_identity, config.security.MAX_IDENTITY_LENGTH) or "iron-man"

    api_key = config.livekit.API_KEY
    api_secret = config.livekit.API_SECRET

    if not api_key or not api_secret:
        logger.error("LiveKit credentials missing in environment")
        return web.json_response(
            {"error": "LiveKit credentials not configured in environment (LIVEKIT_API_KEY/LIVEKIT_API_SECRET)"},
            status=500,
            headers=get_cors_headers(request),
        )

    try:
        from datetime import timedelta
        token = (
            AccessToken(api_key, api_secret)
            .with_identity(identity)
            .with_name("Iron Mon")
            .with_grants(VideoGrants(room_join=True, room=room_name))
            .with_ttl(timedelta(seconds=config.livekit.TOKEN_EXPIRY_SECONDS))
        )
        jwt_token = token.to_jwt()
        metrics.increment("tokens_generated")
        logger.info("Generated LiveKit token for user '%s' in room '%s'", identity, room_name)

        return web.json_response({
            "token": jwt_token,
            "url": config.livekit.URL,
            "room_name": room_name,
            "identity": identity,
        }, headers=get_cors_headers(request))

    except Exception as exc:
        logger.error("Token generation failed: %s", exc)
        return web.json_response(
            {"error": f"Failed to mint session token: {str(exc)}"},
            status=500,
            headers=get_cors_headers(request),
        )


def create_app() -> web.Application:
    app = web.Application()
    app.add_routes(routes)
    return app


if __name__ == "__main__":
    host = config.server.TOKEN_SERVER_HOST
    port = config.server.TOKEN_SERVER_PORT
    print(f"Starting F.R.I.D.A.Y. Token & Health Server on http://{host}:{port}")
    web.run_app(create_app(), host=host, port=port, print=None)
