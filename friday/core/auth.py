"""
F.R.I.D.A.Y. V3 — Identity, Authentication & Scoped Authorization
================================================================
Prevents IDOR and spoofed identities. Binds user identity to all downstream
orders, payments, memories, and bookings.
Enforces granular permission scopes.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Set, Optional
import hmac
import hashlib
import time
from friday.core.logging import get_logger

logger = get_logger("auth_service")


class PermissionScope(str, Enum):
    BOOKING_READ = "booking:read"
    BOOKING_CREATE = "booking:create"
    BOOKING_CANCEL = "booking:cancel"
    PAYMENT_CREATE = "payment:create"
    PAYMENT_READ = "payment:read"
    REFUND_CREATE = "refund:create"
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    TASK_READ = "task:read"
    TASK_WRITE = "task:write"


ALL_STANDARD_SCOPES: Set[PermissionScope] = {
    PermissionScope.BOOKING_READ,
    PermissionScope.BOOKING_CREATE,
    PermissionScope.BOOKING_CANCEL,
    PermissionScope.PAYMENT_CREATE,
    PermissionScope.PAYMENT_READ,
    PermissionScope.REFUND_CREATE,
    PermissionScope.MEMORY_READ,
    PermissionScope.MEMORY_WRITE,
    PermissionScope.TASK_READ,
    PermissionScope.TASK_WRITE,
}


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    username: str
    scopes: Set[PermissionScope] = field(default_factory=lambda: set(ALL_STANDARD_SCOPES))
    is_authenticated: bool = True

    def has_permission(self, required_scope: PermissionScope) -> bool:
        return required_scope in self.scopes

    def assert_permission(self, required_scope: PermissionScope) -> None:
        if not self.has_permission(required_scope):
            raise PermissionError(f"User '{self.user_id}' lacks required permission '{required_scope.value}'.")


class SecurityTokenManager:
    """Signs and verifies lightweight session bearer tokens to prevent spoofing."""

    def __init__(self, secret: str = "friday_stark_sec_token_secret_key_v3"):
        self.secret = secret.encode("utf-8")

    def mint_user_token(self, user_id: str, ttl_seconds: int = 86400) -> str:
        """Create a tamper-proof session token."""
        expires = int(time.time()) + ttl_seconds
        payload = f"{user_id}:{expires}"
        sig = hmac.new(self.secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{payload}:{sig}"

    def verify_user_token(self, token: str) -> Optional[AuthenticatedUser]:
        """Verify token and return AuthenticatedUser if valid."""
        try:
            parts = token.split(":")
            if len(parts) != 3:
                return None
            user_id, expires_str, sig = parts
            expires = int(expires_str)
            if time.time() > expires:
                return None

            expected_sig = hmac.new(self.secret, f"{user_id}:{expires}".encode("utf-8"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected_sig, sig):
                return None

            return AuthenticatedUser(user_id=user_id, username=user_id)
        except Exception as exc:
            logger.warning("Token verification failed: %s", exc)
            return None


security_token_manager = SecurityTokenManager()


def verify_user_ownership(authenticated_user_id: str, resource_user_id: str) -> None:
    """IDOR defense: Asserts user only operates on their own orders/bookings."""
    if authenticated_user_id != resource_user_id:
        raise PermissionError(
            f"Unauthorized access: User '{authenticated_user_id}' cannot access resources belonging to '{resource_user_id}'."
        )
