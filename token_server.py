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

import base64
import json
import os
import re
import secrets
import smtplib
import sqlite3
import ssl
import time
import asyncio
from collections import defaultdict
from email.message import EmailMessage
from aiohttp import web
from livekit.api import AccessToken, VideoGrants

from friday.config import config
from friday.core.local_auth import LocalAuthStore
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
auth_otp_rate_limiter = RateLimiter(max_requests=5, window_seconds=300)
auth_verify_rate_limiter = RateLimiter(max_requests=10, window_seconds=300)
auth_otp_recipient_limiter = RateLimiter(max_requests=3, window_seconds=600)
_local_auth_store: LocalAuthStore | None = None

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
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
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
    supabase_api_key = config.database.SUPABASE_API_KEY
    supabase_anon_key = None
    if supabase_api_key.startswith("sb_publishable_"):
        supabase_anon_key = supabase_api_key
    elif supabase_api_key.count(".") == 2:
        try:
            encoded_payload = supabase_api_key.split(".")[1]
            payload = json.loads(
                base64.urlsafe_b64decode(encoded_payload + "=" * (-len(encoded_payload) % 4))
            )
            if isinstance(payload, dict) and payload.get("role") == "anon":
                supabase_anon_key = supabase_api_key
        except (ValueError, json.JSONDecodeError):
            logger.warning("Supabase API key is not a valid public anon key")
    return web.json_response({
        "server_name": config.server.SERVER_NAME,
        "default_room": config.livekit.DEFAULT_ROOM,
        "environment": config.env.APP_ENV,
        "supabase_url": config.database.SUPABASE_URL or None,
        "supabase_anon_key": supabase_anon_key,
        "features": {
            "web_search": config.features.ENABLE_WEB_SEARCH,
            "memory": config.features.ENABLE_MEMORY,
            "tasks": config.features.ENABLE_TASKS,
            "database": config.features.ENABLE_DATABASE,
        }
    }, headers=get_cors_headers(request))


@routes.options("/api/token")
@routes.options("/api/auth/otp")
@routes.options("/api/auth/verify")
@routes.options("/api/auth/google")
@routes.options("/api/auth/session")
@routes.options("/api/auth/refresh")
@routes.options("/api/conversations")
@routes.options(r"/api/conversations/{conversation_id}")
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


def _auth_store() -> LocalAuthStore:
    global _local_auth_store
    if _local_auth_store is None:
        _local_auth_store = LocalAuthStore(
            os.getenv("FRIDAY_AUTH_DB_PATH", ".friday_data/auth.sqlite3")
        )
    return _local_auth_store


async def _deliver_otp(channel: str, identifier: str, code: str) -> str | None:
    if channel != "email":
        return "Only email verification is currently supported."

    host = os.getenv("SMTP_HOST", "").strip()
    sender = os.getenv("SMTP_FROM", "").strip()
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    try:
        port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError:
        return "Email delivery is misconfigured: SMTP_PORT must be a number."
    if not host or not sender or bool(username) != bool(password):
        return "Email OTP is not configured. Set SMTP_HOST, SMTP_FROM, and matching SMTP_USERNAME/SMTP_PASSWORD values."

    message = EmailMessage()
    message["Subject"] = "Your FRIDAY verification code"
    message["From"] = sender
    message["To"] = identifier
    message.set_content(
        f"Your FRIDAY verification code is {code}. It expires in 10 minutes."
    )

    def send_email() -> None:
        context = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=context, timeout=15) as client:
                if username:
                    client.login(username, password)
                client.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=15) as client:
                client.starttls(context=context)
                if username:
                    client.login(username, password)
                client.send_message(message)

    try:
        await asyncio.to_thread(send_email)
    except (OSError, smtplib.SMTPException):
        logger.exception("Email OTP delivery failed")
        return "Unable to deliver the email code. Check the SMTP settings and try again."
    return None


def _auth_rate_allowed(request: web.Request, limiter: RateLimiter) -> bool:
    return limiter.is_allowed(request.remote or "unknown")


async def _authenticated_user(request: web.Request) -> tuple[dict | None, web.Response | None]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer ") or not auth_header[7:].strip():
        return None, web.json_response(
            {"error": "Sign in to access saved conversations."},
            status=401,
            headers=get_cors_headers(request),
        )
    try:
        user = _auth_store().validate_access_token(auth_header[7:].strip())
    except (OSError, sqlite3.Error):
        logger.exception("Local authentication database lookup failed")
        return None, web.json_response(
            {"error": "Unable to validate your session."}, status=500, headers=get_cors_headers(request)
        )
    if user is None:
        return None, web.json_response(
            {"error": "Sign in again to access saved conversations."},
            status=401,
            headers=get_cors_headers(request),
        )
    return user, None


@routes.get("/api/conversations")
async def list_user_conversations(request: web.Request):
    user, error_response = await _authenticated_user(request)
    if error_response:
        return error_response
    try:
        conversations = _auth_store().list_conversations(user["id"])
    except (OSError, sqlite3.Error, ValueError):
        logger.exception("Local conversation list failed")
        return web.json_response(
            {"error": "Unable to load saved conversations right now."},
            status=500,
            headers=get_cors_headers(request),
        )
    return web.json_response({"conversations": conversations}, headers=get_cors_headers(request))


@routes.put(r"/api/conversations/{conversation_id}")
async def save_user_conversation(request: web.Request):
    import re

    user, error_response = await _authenticated_user(request)
    if error_response:
        return error_response
    conversation_id = request.match_info["conversation_id"]
    if not re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        conversation_id,
    ):
        return web.json_response(
            {"error": "Invalid conversation id."}, status=400, headers=get_cors_headers(request)
        )
    try:
        data = await request.json()
    except (ValueError, web.HTTPBadRequest):
        return web.json_response({"error": "Invalid conversation data."}, status=400, headers=get_cors_headers(request))
    if not isinstance(data, dict):
        return web.json_response({"error": "Invalid conversation data."}, status=400, headers=get_cors_headers(request))
    title = data.get("title")
    updated_at = data.get("updated_at")
    messages = data.get("messages")
    if (
        data.get("id") != conversation_id
        or not isinstance(title, str)
        or len(title) > 255
        or not isinstance(updated_at, str)
        or not isinstance(messages, list)
        or len(messages) > 2000
    ):
        return web.json_response(
            {"error": "Conversation data is invalid or too large."},
            status=400,
            headers=get_cors_headers(request),
        )
    for message in messages:
        if (
            not isinstance(message, dict)
            or not isinstance(message.get("id"), str)
            or message.get("role") not in ("user", "assistant")
            or not isinstance(message.get("text"), str)
            or len(message["text"]) > 20000
            or not isinstance(message.get("timestamp"), str)
        ):
            return web.json_response(
                {"error": "Conversation contains an invalid message."},
                status=400,
                headers=get_cors_headers(request),
            )
    try:
        saved = _auth_store().save_conversation(
            user["id"], conversation_id, title, updated_at, messages
        )
    except (OSError, sqlite3.Error, TypeError, ValueError):
        logger.exception("Local conversation save failed")
        return web.json_response(
            {"error": "Unable to save conversations right now."},
            status=500,
            headers=get_cors_headers(request),
        )
    if not saved:
        return web.json_response(
            {"error": "Conversation not found."}, status=404, headers=get_cors_headers(request)
        )
    return web.json_response({"saved": True}, headers=get_cors_headers(request))


@routes.delete(r"/api/conversations/{conversation_id}")
async def delete_user_conversation(request: web.Request):
    import re

    user, error_response = await _authenticated_user(request)
    if error_response:
        return error_response
    conversation_id = request.match_info["conversation_id"]
    if not re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        conversation_id,
    ):
        return web.json_response(
            {"error": "Invalid conversation id."}, status=400, headers=get_cors_headers(request)
        )
    try:
        _auth_store().delete_conversation(user["id"], conversation_id)
    except (OSError, sqlite3.Error):
        logger.exception("Local conversation delete failed")
        return web.json_response(
            {"error": "Unable to delete the saved conversation right now."},
            status=500,
            headers=get_cors_headers(request),
        )
    return web.json_response({"deleted": True}, headers=get_cors_headers(request))


@routes.post("/api/auth/otp")
async def request_auth_otp(request: web.Request):
    """Send a one-time email or SMS code for account access."""
    if not _auth_rate_allowed(request, auth_otp_rate_limiter):
        return web.json_response(
            {"error": "Too many code requests. Please wait before trying again."},
            status=429,
            headers=get_cors_headers(request),
        )
    try:
        data = await request.json()
    except (ValueError, web.HTTPBadRequest):
        return web.json_response({"error": "Invalid request."}, status=400, headers=get_cors_headers(request))
    if not isinstance(data, dict):
        return web.json_response({"error": "Invalid request."}, status=400, headers=get_cors_headers(request))

    channel = data.get("channel")
    identifier = data.get("identifier")
    mode = data.get("mode")
    if not isinstance(identifier, str) or mode not in ("signup", "signin") or channel != "email":
        return web.json_response({"error": "Enter a valid email address."}, status=400, headers=get_cors_headers(request))
    identifier = identifier.strip().lower()
    valid_identifier = len(identifier) <= 254 and re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", identifier)
    if not valid_identifier:
        return web.json_response(
            {"error": "Enter a valid email address."},
            status=400,
            headers=get_cors_headers(request),
        )

    recipient_key = f"{channel}:{identifier}"
    if not auth_otp_recipient_limiter.is_allowed(recipient_key):
        return web.json_response(
            {"error": "Too many codes requested for this address. Please wait and try again."},
            status=429,
            headers=get_cors_headers(request),
        )
    code = f"{secrets.randbelow(1_000_000):06d}"
    delivery_error = await _deliver_otp(channel, identifier, code)
    if delivery_error:
        status = 503 if "not configured" in delivery_error or "misconfigured" in delivery_error else 502
        return web.json_response({"error": delivery_error}, status=status, headers=get_cors_headers(request))
    try:
        _auth_store().save_otp(channel, identifier, mode, code)
    except (OSError, sqlite3.Error):
        logger.exception("Unable to persist the OTP challenge")
        return web.json_response(
            {"error": "The code was sent, but the authentication service could not save it. Please request a new code."},
            status=500,
            headers=get_cors_headers(request),
        )
    return web.json_response({"message": "Verification code sent."}, headers=get_cors_headers(request))


@routes.post("/api/auth/verify")
async def verify_auth_otp(request: web.Request):
    """Verify a one-time code and issue local bearer and refresh tokens."""
    if not _auth_rate_allowed(request, auth_verify_rate_limiter):
        return web.json_response(
            {"error": "Too many verification attempts. Please wait before trying again."},
            status=429,
            headers=get_cors_headers(request),
        )
    try:
        data = await request.json()
    except (ValueError, web.HTTPBadRequest):
        return web.json_response({"error": "Invalid request."}, status=400, headers=get_cors_headers(request))
    if not isinstance(data, dict):
        return web.json_response({"error": "Invalid request."}, status=400, headers=get_cors_headers(request))

    channel = data.get("channel")
    identifier = data.get("identifier")
    code = data.get("code")
    mode = data.get("mode")
    if not isinstance(identifier, str) or not isinstance(code, str) or mode not in ("signup", "signin"):
        return web.json_response({"error": "Enter the address, access type, and six-digit code."}, status=400, headers=get_cors_headers(request))
    identifier = identifier.strip()
    identifier = identifier.lower()
    if channel != "email" or not re.fullmatch(r"\d{6}", code):
        return web.json_response(
            {"error": "Enter the six-digit verification code."}, status=400, headers=get_cors_headers(request)
        )
    try:
        session = await asyncio.to_thread(
            _auth_store().verify_otp, channel, identifier, mode, code
        )
    except (OSError, sqlite3.Error):
        logger.exception("Local OTP verification failed")
        return web.json_response(
            {"error": "Unable to verify the code right now. Please try again later."},
            status=500,
            headers=get_cors_headers(request),
        )
    if session is None:
        return web.json_response(
            {"error": "That code is invalid, expired, or cannot be used for this account. Request a new code and try again."},
            status=401,
            headers=get_cors_headers(request),
        )
    return web.json_response(session, headers=get_cors_headers(request))


@routes.post("/api/auth/session")
async def validate_auth_session(request: web.Request):
    """Validate a saved local access token."""
    try:
        data = await request.json()
    except (ValueError, web.HTTPBadRequest):
        return web.json_response({"error": "Invalid request."}, status=400, headers=get_cors_headers(request))
    if not isinstance(data, dict):
        return web.json_response({"error": "Invalid request."}, status=400, headers=get_cors_headers(request))
    access_token = data.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        return web.json_response({"error": "Sign in again to continue."}, status=401, headers=get_cors_headers(request))
    try:
        user = _auth_store().validate_access_token(access_token)
    except (OSError, sqlite3.Error):
        logger.exception("Local session validation failed")
        return web.json_response({"error": "Unable to validate your session."}, status=500, headers=get_cors_headers(request))
    if user is None:
        return web.json_response({"error": "Sign in again to continue."}, status=401, headers=get_cors_headers(request))
    return web.json_response({"user": user}, headers=get_cors_headers(request))


@routes.post("/api/auth/google")
async def authenticate_google_user(request: web.Request):
    """Validate a Supabase OAuth access token and issue a local application session."""
    import httpx

    if not config.database.SUPABASE_URL or not config.database.SUPABASE_API_KEY:
        return web.json_response(
            {"error": "Google sign-in is not configured on the server."},
            status=503,
            headers=get_cors_headers(request),
        )
    try:
        data = await request.json()
    except (ValueError, web.HTTPBadRequest):
        return web.json_response({"error": "Invalid request."}, status=400, headers=get_cors_headers(request))
    if not isinstance(data, dict):
        return web.json_response({"error": "Invalid request."}, status=400, headers=get_cors_headers(request))
    access_token = data.get("access_token")
    if not isinstance(access_token, str) or not access_token or len(access_token) > 8192:
        return web.json_response({"error": "Google sign-in did not return a valid session."}, status=401, headers=get_cors_headers(request))

    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get(
                f"{config.database.SUPABASE_URL.rstrip('/')}/auth/v1/user",
                headers={
                    "apikey": config.database.SUPABASE_API_KEY,
                    "Authorization": f"Bearer {access_token}",
                },
            )
    except httpx.HTTPError:
        logger.exception("Supabase Google token validation failed")
        return web.json_response(
            {"error": "Unable to validate your Google sign-in right now."},
            status=502,
            headers=get_cors_headers(request),
        )
    if response.is_error:
        return web.json_response(
            {"error": "Google sign-in could not be verified. Please try again."},
            status=401,
            headers=get_cors_headers(request),
        )
    try:
        provider_user = response.json()
    except ValueError:
        logger.error("Supabase returned malformed user data for Google sign-in")
        return web.json_response(
            {"error": "The authentication service returned an invalid response."},
            status=502,
            headers=get_cors_headers(request),
        )

    email = provider_user.get("email") if isinstance(provider_user, dict) else None
    user_metadata = provider_user.get("user_metadata", {}) if isinstance(provider_user, dict) else {}
    display_name = None
    if isinstance(user_metadata, dict):
        display_name = user_metadata.get("full_name") or user_metadata.get("name")
    if not isinstance(display_name, str) or not display_name.strip():
        display_name = None
    elif len(display_name.strip()) > 120:
        display_name = display_name.strip()[:120]
    verified = bool(
        isinstance(provider_user, dict)
        and (provider_user.get("email_confirmed_at") or provider_user.get("confirmed_at"))
    )
    if not isinstance(email, str) or not verified:
        return web.json_response(
            {"error": "Google must provide a verified email address to sign in."},
            status=403,
            headers=get_cors_headers(request),
        )

    try:
        session = await asyncio.to_thread(
            _auth_store().login_with_verified_email,
            email.strip().lower(),
            display_name,
        )
    except (OSError, sqlite3.Error):
        logger.exception("Unable to create local session for verified Google user")
        return web.json_response(
            {"error": "Unable to create your application session right now."},
            status=500,
            headers=get_cors_headers(request),
        )
    return web.json_response(session, headers=get_cors_headers(request))


@routes.post("/api/auth/refresh")
async def refresh_auth_session(request: web.Request):
    """Rotate local access and refresh tokens."""
    try:
        data = await request.json()
    except (ValueError, web.HTTPBadRequest):
        return web.json_response({"error": "Invalid request."}, status=400, headers=get_cors_headers(request))
    if not isinstance(data, dict):
        return web.json_response({"error": "Invalid request."}, status=400, headers=get_cors_headers(request))
    refresh_token = data.get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token:
        return web.json_response({"error": "Sign in again to continue."}, status=401, headers=get_cors_headers(request))
    try:
        session = _auth_store().refresh_session(refresh_token)
    except (OSError, sqlite3.Error):
        logger.exception("Local session refresh failed")
        return web.json_response({"error": "Unable to refresh your session."}, status=500, headers=get_cors_headers(request))
    if session is None:
        return web.json_response({"error": "Sign in again to continue."}, status=401, headers=get_cors_headers(request))
    return web.json_response(session, headers=get_cors_headers(request))


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
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        access_token = auth_header[7:].strip()
        if not access_token:
            return web.json_response({"error": "Sign in again to connect."}, status=401, headers=get_cors_headers(request))
        try:
            authenticated_user = _auth_store().validate_access_token(access_token)
        except (OSError, sqlite3.Error):
            logger.exception("Local token validation failed before LiveKit connection")
            return web.json_response(
                {"error": "Unable to validate your session before connecting."},
                status=500,
                headers=get_cors_headers(request),
            )
        if authenticated_user is None:
            return web.json_response({"error": "Sign in again to connect."}, status=401, headers=get_cors_headers(request))
        raw_identity = authenticated_user["id"]
        identity = sanitize_string(raw_identity, config.security.MAX_IDENTITY_LENGTH)
        room_name = sanitize_string(f"friday-{identity}", config.security.MAX_ROOM_NAME_LENGTH)
    else:
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
