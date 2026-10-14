"""
F.R.I.D.A.Y. V2 — Structured Error System
==========================================
Categorized exceptions for every layer of the application.
Each error carries a user-friendly message that FRIDAY can speak.
"""


class FridayError(Exception):
    """Base exception for all FRIDAY errors."""

    def __init__(self, message: str, user_message: str | None = None, details: dict | None = None):
        super().__init__(message)
        self.user_message = user_message or "Something went wrong, boss. I'm looking into it."
        self.details = details or {}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ValidationError(FridayError):
    """Invalid input or parameters."""

    def __init__(self, message: str, field: str | None = None, **kwargs):
        super().__init__(
            message,
            user_message=kwargs.get("user_message", "That doesn't look right, boss. Could you try again?"),
            details={"field": field, **kwargs.get("details", {})},
        )


# ---------------------------------------------------------------------------
# Authentication & Authorization
# ---------------------------------------------------------------------------

class AuthenticationError(FridayError):
    """User is not authenticated."""

    def __init__(self, message: str = "Authentication required", **kwargs):
        super().__init__(
            message,
            user_message="I need to verify your identity first, boss.",
            details=kwargs.get("details", {}),
        )


class AuthorizationError(FridayError):
    """User lacks permission for this action."""

    def __init__(self, message: str = "Insufficient permissions", action: str = "", **kwargs):
        super().__init__(
            message,
            user_message=f"I'm not authorized to do that without clearance, boss.",
            details={"action": action, **kwargs.get("details", {})},
        )


# ---------------------------------------------------------------------------
# Network & External Services
# ---------------------------------------------------------------------------

class NetworkError(FridayError):
    """Network connectivity issue."""

    def __init__(self, message: str, service: str = "", **kwargs):
        super().__init__(
            message,
            user_message=f"I'm having trouble reaching an external service right now, boss.",
            details={"service": service, **kwargs.get("details", {})},
        )


class ProviderError(FridayError):
    """AI provider (STT/LLM/TTS) failure."""

    def __init__(self, message: str, provider: str = "", provider_type: str = "", **kwargs):
        super().__init__(
            message,
            user_message=kwargs.get(
                "user_message",
                f"The {provider_type} service had a hiccup. I've switched to the backup."
            ),
            details={"provider": provider, "provider_type": provider_type, **kwargs.get("details", {})},
        )


class ProviderUnavailableError(ProviderError):
    """All providers for a service type are unavailable."""

    def __init__(self, provider_type: str, **kwargs):
        super().__init__(
            f"All {provider_type} providers are unavailable",
            provider_type=provider_type,
            user_message=f"I'm unable to process that right now — the {provider_type} systems are all offline, boss.",
            **kwargs,
        )


# ---------------------------------------------------------------------------
# MCP
# ---------------------------------------------------------------------------

class MCPError(FridayError):
    """MCP server or tool error."""

    def __init__(self, message: str, tool: str = "", **kwargs):
        super().__init__(
            message,
            user_message="One of my tools ran into an issue, boss. Let me try another approach.",
            details={"tool": tool, **kwargs.get("details", {})},
        )


class ToolExecutionError(MCPError):
    """A specific tool failed during execution."""
    pass


class ToolPermissionError(MCPError):
    """Tool requires higher permission level."""

    def __init__(self, tool: str, required_level: str, **kwargs):
        super().__init__(
            f"Tool '{tool}' requires permission level: {required_level}",
            tool=tool,
            **kwargs,
        )
        self.user_message = "That action requires additional authorization, boss."


class ToolRateLimitError(MCPError):
    """Too many tool calls in a single turn."""

    def __init__(self, tool: str = "", limit: int = 0, **kwargs):
        super().__init__(
            f"Tool call limit reached ({limit})",
            tool=tool,
            **kwargs,
        )
        self.user_message = "I've hit my operational limit for this turn, boss. Let me wrap up what I have."


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

class DatabaseError(FridayError):
    """Database operation failure."""

    def __init__(self, message: str, operation: str = "", **kwargs):
        super().__init__(
            message,
            user_message="My memory systems are experiencing a glitch, boss. The data might not be saved.",
            details={"operation": operation, **kwargs.get("details", {})},
        )


class DatabaseNotConfiguredError(DatabaseError):
    """Database is not configured but a DB operation was attempted."""

    def __init__(self):
        super().__init__(
            "Database not configured — SUPABASE_URL and SUPABASE_API_KEY required",
            operation="connect",
        )
        self.user_message = "My long-term storage isn't set up yet, boss."


# ---------------------------------------------------------------------------
# LiveKit
# ---------------------------------------------------------------------------

class LiveKitError(FridayError):
    """LiveKit connection or room error."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            user_message="The communication channel is having issues, boss.",
            details=kwargs.get("details", {}),
        )


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------

class TimeoutError(FridayError):
    """Operation timed out."""

    def __init__(self, message: str, operation: str = "", timeout_seconds: float = 0, **kwargs):
        super().__init__(
            message,
            user_message="That's taking longer than expected, boss. Let me try again.",
            details={"operation": operation, "timeout_seconds": timeout_seconds, **kwargs.get("details", {})},
        )


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class ConfigurationError(FridayError):
    """Application misconfiguration."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            user_message="There's a configuration issue on my end, boss. The team needs to take a look.",
            details=kwargs.get("details", {}),
        )


# ---------------------------------------------------------------------------
# Confirmation
# ---------------------------------------------------------------------------

class ConfirmationRequired(FridayError):
    """Action requires user confirmation before execution."""

    def __init__(self, action: str, description: str = ""):
        super().__init__(
            f"Confirmation required for action: {action}",
            user_message=description or f"Shall I go ahead with that, boss?",
            details={"action": action, "description": description, "awaiting_confirmation": True},
        )
