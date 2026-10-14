"""
F.R.I.D.A.Y. V2 — Structured Logging
=====================================
Centralized logging with structured output, configurable levels,
and sanitization to prevent secret leakage.
"""

import logging
import sys
import time
import functools
from typing import Any

from friday.config.settings import config

# Sensitive keys that must never be logged
_SENSITIVE_KEYS = frozenset({
    "api_key", "api_secret", "secret", "password", "token", "jwt",
    "authorization", "credential", "SARVAM_API_KEY", "OPENAI_API_KEY",
    "GOOGLE_API_KEY", "SUPABASE_API_KEY", "SUPABASE_SERVICE_KEY",
    "LIVEKIT_API_SECRET", "AUTH_SECRET", "GROQ_API_KEY", "DEEPGRAM_API_KEY",
})


def _sanitize_value(key: str, value: Any) -> Any:
    """Redact sensitive values in log output."""
    if isinstance(key, str) and key.lower().replace("-", "_") in {k.lower() for k in _SENSITIVE_KEYS}:
        if isinstance(value, str) and len(value) > 4:
            return value[:4] + "****"
        return "****"
    return value


def sanitize_dict(data: dict) -> dict:
    """Recursively sanitize a dictionary for safe logging."""
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        else:
            sanitized[key] = _sanitize_value(key, value)
    return sanitized


class FridayFormatter(logging.Formatter):
    """Custom formatter with structured context fields."""

    COLORS = {
        logging.DEBUG: "\033[36m",      # Cyan
        logging.INFO: "\033[32m",       # Green
        logging.WARNING: "\033[33m",    # Yellow
        logging.ERROR: "\033[31m",      # Red
        logging.CRITICAL: "\033[35m",   # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, use_color: bool = True):
        super().__init__()
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        level = record.levelname
        if self.use_color:
            color = self.COLORS.get(record.levelno, "")
            level = f"{color}{level}{self.RESET}"

        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        name = record.name

        # Build base message
        msg = f"[{timestamp}] {level:>20s} | {name} | {record.getMessage()}"

        # Append structured context if present
        ctx = getattr(record, "context", None)
        if ctx and isinstance(ctx, dict):
            ctx_str = " | ".join(f"{k}={v}" for k, v in sanitize_dict(ctx).items())
            msg += f" | {ctx_str}"

        # Append exception info
        if record.exc_info and record.exc_info[2]:
            msg += "\n" + self.formatException(record.exc_info)

        return msg


def setup_logging(name: str = "friday") -> logging.Logger:
    """Configure and return the application root logger."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    level_str = config.env.LOG_LEVEL.upper()
    level = getattr(logging, level_str, logging.INFO)
    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(FridayFormatter(use_color=not config.env.is_production))
    logger.addHandler(handler)

    # Suppress noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "hpack"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the friday namespace."""
    setup_logging("friday")
    return logging.getLogger(f"friday.{name}")


class LogContext:
    """Context manager / decorator that adds structured fields to log records."""

    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context

    def _log(self, level: int, msg: str, *args, **kwargs):
        extra = kwargs.pop("extra", {})
        extra["context"] = {**self.context, **kwargs.pop("context", {})}
        self.logger.log(level, msg, *args, extra=extra, **kwargs)

    def debug(self, msg: str, **kwargs):
        self._log(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs):
        self._log(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs):
        self._log(logging.ERROR, msg, **kwargs)

    def critical(self, msg: str, **kwargs):
        self._log(logging.CRITICAL, msg, **kwargs)


def log_latency(logger: logging.Logger | None = None, operation: str = ""):
    """Decorator to log execution time of async/sync functions."""
    def decorator(func):
        _logger = logger or get_logger(func.__module__ or "unknown")

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                result = await func(*args, **kwargs)
                elapsed = (time.monotonic() - start) * 1000
                _logger.info(
                    "%s completed",
                    operation or func.__name__,
                    extra={"context": {"latency_ms": f"{elapsed:.1f}"}},
                )
                return result
            except Exception as exc:
                elapsed = (time.monotonic() - start) * 1000
                _logger.error(
                    "%s failed: %s",
                    operation or func.__name__,
                    str(exc),
                    extra={"context": {"latency_ms": f"{elapsed:.1f}", "error": type(exc).__name__}},
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                result = func(*args, **kwargs)
                elapsed = (time.monotonic() - start) * 1000
                _logger.info(
                    "%s completed",
                    operation or func.__name__,
                    extra={"context": {"latency_ms": f"{elapsed:.1f}"}},
                )
                return result
            except Exception as exc:
                elapsed = (time.monotonic() - start) * 1000
                _logger.error(
                    "%s failed: %s",
                    operation or func.__name__,
                    str(exc),
                    extra={"context": {"latency_ms": f"{elapsed:.1f}", "error": type(exc).__name__}},
                )
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
