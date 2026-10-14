"""
F.R.I.D.A.Y. V2 — Health Checks
================================
Health check endpoints and dependency status checks.
"""

import time
from dataclasses import dataclass, field
from typing import Optional

from friday.config import config
from friday.core.logging import get_logger

logger = get_logger("health")


@dataclass
class ServiceHealth:
    name: str
    status: str  # "healthy", "unhealthy", "degraded", "unconfigured"
    message: str = ""
    latency_ms: Optional[float] = None


@dataclass
class HealthReport:
    status: str  # "healthy", "degraded", "unhealthy"
    uptime_seconds: float = 0
    services: list[ServiceHealth] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "uptime_seconds": round(self.uptime_seconds, 1),
            "services": {
                s.name: {
                    "status": s.status,
                    "message": s.message,
                    **({"latency_ms": round(s.latency_ms, 1)} if s.latency_ms else {}),
                }
                for s in self.services
            },
        }


class HealthChecker:
    """Checks health of all FRIDAY dependencies."""

    def __init__(self):
        self._start_time = time.monotonic()

    @property
    def uptime(self) -> float:
        return time.monotonic() - self._start_time

    def check_livekit(self) -> ServiceHealth:
        if config.livekit.is_configured:
            return ServiceHealth("livekit", "healthy", "Credentials configured")
        return ServiceHealth("livekit", "unconfigured", "Missing LiveKit credentials")

    def check_database(self) -> ServiceHealth:
        if not config.features.ENABLE_DATABASE:
            return ServiceHealth("database", "unconfigured", "Database feature disabled")
        if config.database.is_configured:
            return ServiceHealth("database", "healthy", "Supabase configured")
        return ServiceHealth("database", "unconfigured", "Missing Supabase credentials")

    def check_providers(self) -> list[ServiceHealth]:
        results = []

        # STT
        if config.providers.PRIMARY_STT == "sarvam" and config.providers.SARVAM_API_KEY:
            results.append(ServiceHealth("stt_primary", "healthy", "Sarvam configured"))
        elif config.providers.PRIMARY_STT == "whisper" and config.providers.OPENAI_API_KEY:
            results.append(ServiceHealth("stt_primary", "healthy", "Whisper configured"))
        else:
            results.append(ServiceHealth("stt_primary", "unhealthy", "STT provider not configured"))

        # LLM
        if config.providers.PRIMARY_LLM == "groq" and config.providers.GROQ_API_KEY:
            results.append(ServiceHealth("llm_primary", "healthy", "Groq configured"))
        elif config.providers.PRIMARY_LLM == "gemini" and config.providers.GOOGLE_API_KEY:
            results.append(ServiceHealth("llm_primary", "healthy", "Gemini configured"))
        elif config.providers.PRIMARY_LLM == "openai" and config.providers.OPENAI_API_KEY:
            results.append(ServiceHealth("llm_primary", "healthy", "OpenAI configured"))
        else:
            results.append(ServiceHealth("llm_primary", "unhealthy", "LLM provider not configured"))

        # TTS
        if config.providers.PRIMARY_TTS == "openai" and config.providers.OPENAI_API_KEY:
            results.append(ServiceHealth("tts_primary", "healthy", "OpenAI TTS configured"))
        elif config.providers.PRIMARY_TTS == "sarvam" and config.providers.SARVAM_API_KEY:
            results.append(ServiceHealth("tts_primary", "healthy", "Sarvam TTS configured"))
        else:
            results.append(ServiceHealth("tts_primary", "unhealthy", "TTS provider not configured"))

        return results

    def check_all(self) -> HealthReport:
        """Run all health checks and return a report."""
        services: list[ServiceHealth] = []

        services.append(self.check_livekit())
        services.append(self.check_database())
        services.extend(self.check_providers())

        # Determine overall status
        statuses = [s.status for s in services]
        if all(s in ("healthy", "unconfigured") for s in statuses):
            overall = "healthy"
        elif any(s == "unhealthy" for s in statuses):
            overall = "unhealthy"
        else:
            overall = "degraded"

        return HealthReport(
            status=overall,
            uptime_seconds=self.uptime,
            services=services,
        )

    def check_liveness(self) -> dict:
        """Minimal liveness probe — is the process alive?"""
        return {"status": "alive", "uptime_seconds": round(self.uptime, 1)}

    def check_readiness(self) -> dict:
        """Readiness probe — can the server accept requests?"""
        report = self.check_all()
        return {
            "ready": report.status != "unhealthy",
            "status": report.status,
        }


# Singleton
health_checker = HealthChecker()


def get_health_report() -> HealthReport:
    """Convenience function returning full health report."""
    return health_checker.check_all()
