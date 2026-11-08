"""
F.R.I.D.A.Y. V2 — Centralized Configuration
=============================================
All application settings loaded from environment variables with sensible defaults.
Supports development, testing, and production environments.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Any
from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _env_bool(key: str, default: bool = False) -> bool:
    return _env(key, str(default)).lower() in ("true", "1", "yes")


def _env_int(key: str, default: int = 0) -> int:
    try:
        return int(_env(key, str(default)))
    except ValueError:
        return default


def _env_float(key: str, default: float = 0.0) -> float:
    try:
        return float(_env(key, str(default)))
    except ValueError:
        return default


def _env_list(key: str, default: str = "") -> list[str]:
    raw = _env(key, default)
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EnvironmentConfig:
    APP_ENV: str = _env("APP_ENV", "development")
    DEBUG: bool = _env_bool("DEBUG", False)
    LOG_LEVEL: str = _env("LOG_LEVEL", "INFO")

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_testing(self) -> bool:
        return self.APP_ENV == "testing"


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ServerConfig:
    SERVER_NAME: str = _env("SERVER_NAME", "Friday")
    MCP_SERVER_HOST: str = _env("MCP_SERVER_HOST", "127.0.0.1")
    MCP_SERVER_PORT: int = _env_int("MCP_SERVER_PORT", 8000)
    MCP_TRANSPORT: str = _env("MCP_TRANSPORT", "sse")
    TOKEN_SERVER_HOST: str = _env("TOKEN_SERVER_HOST", "0.0.0.0")
    TOKEN_SERVER_PORT: int = _env_int("TOKEN_SERVER_PORT", 8080)

    @property
    def mcp_server_url(self) -> str:
        return f"http://{self.MCP_SERVER_HOST}:{self.MCP_SERVER_PORT}/{self.MCP_TRANSPORT}"


# ---------------------------------------------------------------------------
# LiveKit
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LiveKitConfig:
    URL: str = _env("LIVEKIT_URL", "")
    API_KEY: str = _env("LIVEKIT_API_KEY", "")
    API_SECRET: str = _env("LIVEKIT_API_SECRET", "")
    DEFAULT_ROOM: str = _env("LIVEKIT_DEFAULT_ROOM", "friday-lab")
    TOKEN_EXPIRY_SECONDS: int = _env_int("LIVEKIT_TOKEN_EXPIRY", 3600)

    @property
    def is_configured(self) -> bool:
        return bool(self.URL and self.API_KEY and self.API_SECRET)


# ---------------------------------------------------------------------------
# Provider Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProviderConfig:
    # STT
    PRIMARY_STT: str = _env("PRIMARY_STT_PROVIDER", "sarvam")
    FALLBACK_STT: str = _env("FALLBACK_STT_PROVIDER", "whisper")
    SARVAM_API_KEY: str = _env("SARVAM_API_KEY", "")
    SARVAM_STT_MODEL: str = _env("SARVAM_STT_MODEL", "saaras:v3")
    SARVAM_STT_SAMPLE_RATE: int = _env_int("SARVAM_STT_SAMPLE_RATE", 16000)

    # LLM
    PRIMARY_LLM: str = _env("PRIMARY_LLM_PROVIDER", "groq")
    FALLBACK_LLM: str = _env("FALLBACK_LLM_PROVIDER", "gemini")
    GOOGLE_API_KEY: str = _env("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = _env("GEMINI_LLM_MODEL", "gemini-3.5-flash")
    OPENAI_API_KEY: str = _env("OPENAI_API_KEY", "")
    OPENAI_LLM_MODEL: str = _env("OPENAI_LLM_MODEL", "gpt-4o")

    # TTS
    PRIMARY_TTS: str = _env("PRIMARY_TTS_PROVIDER", "sarvam")
    FALLBACK_TTS: str = _env("FALLBACK_TTS_PROVIDER", "openai")
    OPENAI_TTS_MODEL: str = _env("OPENAI_TTS_MODEL", "tts-1")
    OPENAI_TTS_VOICE: str = _env("OPENAI_TTS_VOICE", "nova")
    TTS_SPEED: float = _env_float("TTS_SPEED", 1.15)
    SARVAM_TTS_LANGUAGE: str = _env("SARVAM_TTS_LANGUAGE", "en-IN")
    SARVAM_TTS_SPEAKER: str = _env("SARVAM_TTS_SPEAKER", "rahul")
    SARVAM_TTS_MODEL: str = _env("SARVAM_TTS_MODEL", "bulbul:v3")

    # Groq (primary free LLM)
    GROQ_API_KEY: str = _env("GROQ_API_KEY", "")
    GROQ_MODEL: str = _env("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")
    GROQ_VISION_MODEL: str = _env(
        "GROQ_VISION_MODEL",
        "meta-llama/llama-4-scout-17b-16e-instruct",
    )

    # Deepgram (optional alternate)
    DEEPGRAM_API_KEY: str = _env("DEEPGRAM_API_KEY", "")


# ---------------------------------------------------------------------------
# Database (Supabase)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DatabaseConfig:
    SUPABASE_URL: str = _env("SUPABASE_URL", "")
    SUPABASE_API_KEY: str = _env("SUPABASE_API_KEY", "")
    SUPABASE_SERVICE_KEY: str = _env("SUPABASE_SERVICE_KEY", "")

    @property
    def is_configured(self) -> bool:
        return bool(self.SUPABASE_URL and (self.SUPABASE_API_KEY or self.SUPABASE_SERVICE_KEY))


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SecurityConfig:
    ALLOWED_ORIGINS: list = field(
        default_factory=lambda: _env_list(
            "ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
        )
    )
    AUTH_SECRET: str = _env("AUTH_SECRET", "")
    RATE_LIMIT_REQUESTS: int = _env_int("RATE_LIMIT_REQUESTS", 30)
    RATE_LIMIT_WINDOW_SECONDS: int = _env_int("RATE_LIMIT_WINDOW_SECONDS", 60)
    MAX_ROOM_NAME_LENGTH: int = 64
    MAX_IDENTITY_LENGTH: int = 64


# ---------------------------------------------------------------------------
# Timeouts & Retries
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ResilienceConfig:
    HTTP_CONNECT_TIMEOUT: float = _env_float("HTTP_CONNECT_TIMEOUT", 5.0)
    HTTP_READ_TIMEOUT: float = _env_float("HTTP_READ_TIMEOUT", 10.0)
    HTTP_TOTAL_TIMEOUT: float = _env_float("HTTP_TOTAL_TIMEOUT", 30.0)
    MAX_RETRIES: int = _env_int("MAX_RETRIES", 3)
    RETRY_BACKOFF_BASE: float = _env_float("RETRY_BACKOFF_BASE", 1.5)
    CIRCUIT_BREAKER_THRESHOLD: int = _env_int("CIRCUIT_BREAKER_THRESHOLD", 5)
    CIRCUIT_BREAKER_RESET_SECONDS: int = _env_int("CIRCUIT_BREAKER_RESET_SECONDS", 60)
    MCP_SESSION_TIMEOUT: int = _env_int("MCP_SESSION_TIMEOUT", 30)
    MAX_TOOL_CALLS_PER_TURN: int = _env_int("MAX_TOOL_CALLS_PER_TURN", 10)


# ---------------------------------------------------------------------------
# Feature Flags
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FeatureFlags:
    ENABLE_WEB_SEARCH: bool = _env_bool("ENABLE_WEB_SEARCH", True)
    ENABLE_MEMORY: bool = _env_bool("ENABLE_MEMORY", True)
    ENABLE_TASKS: bool = _env_bool("ENABLE_TASKS", True)
    ENABLE_DATABASE: bool = _env_bool("ENABLE_DATABASE", True)
    ENABLE_WORLD_MONITOR: bool = _env_bool("ENABLE_WORLD_MONITOR", True)
    ENABLE_PROVIDER_FAILOVER: bool = _env_bool("ENABLE_PROVIDER_FAILOVER", True)
    ENABLE_AUTH: bool = _env_bool("ENABLE_AUTH", False)
    ENABLE_RATE_LIMITING: bool = _env_bool("ENABLE_RATE_LIMITING", True)
    ENABLE_HEALTH_CHECKS: bool = _env_bool("ENABLE_HEALTH_CHECKS", True)
    ENABLE_METRICS: bool = _env_bool("ENABLE_METRICS", True)

    # Action & Transactional Feature Flags (Disabled by default)
    ENABLE_BOOKING: bool = _env_bool("ENABLE_BOOKING", False)
    ENABLE_TRAIN_BOOKING: bool = _env_bool("ENABLE_TRAIN_BOOKING", False)
    ENABLE_FLIGHT_BOOKING: bool = _env_bool("ENABLE_FLIGHT_BOOKING", False)
    ENABLE_MOVIE_BOOKING: bool = _env_bool("ENABLE_MOVIE_BOOKING", False)
    ENABLE_HOTEL_BOOKING: bool = _env_bool("ENABLE_HOTEL_BOOKING", False)
    ENABLE_REAL_PAYMENT: bool = _env_bool("ENABLE_REAL_PAYMENT", False)
    ENABLE_REAL_BOOKING: bool = _env_bool("ENABLE_REAL_BOOKING", False)


# ---------------------------------------------------------------------------
# News & Search
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ContentConfig:
    NEWS_FEEDS: list = field(
        default_factory=lambda: _env_list(
            "NEWS_FEEDS",
            "https://feeds.bbci.co.uk/news/world/rss.xml,"
            "https://www.cnbc.com/id/100727362/device/rss/rss.html,"
            "https://rss.nytimes.com/services/xml/rss/nyt/World.xml,"
            "https://www.aljazeera.com/xml/rss/all.xml"
        )
    )
    NEWS_MAX_ARTICLES: int = _env_int("NEWS_MAX_ARTICLES", 12)
    NEWS_ITEMS_PER_FEED: int = _env_int("NEWS_ITEMS_PER_FEED", 5)
    SEARCH_MAX_RESULTS: int = _env_int("SEARCH_MAX_RESULTS", 8)
    FETCH_URL_MAX_CHARS: int = _env_int("FETCH_URL_MAX_CHARS", 4000)
    FETCH_URL_ALLOWED_SCHEMES: list = field(
        default_factory=lambda: ["http", "https"]
    )


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MemoryConfig:
    CONTEXT_WINDOW_SIZE: int = _env_int("CONTEXT_WINDOW_SIZE", 20)
    MAX_LONG_TERM_MEMORIES: int = _env_int("MAX_LONG_TERM_MEMORIES", 100)
    MEMORY_RETRIEVAL_LIMIT: int = _env_int("MEMORY_RETRIEVAL_LIMIT", 10)


# ---------------------------------------------------------------------------
# Composite Config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FridayConfig:
    env: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    livekit: LiveKitConfig = field(default_factory=LiveKitConfig)
    providers: ProviderConfig = field(default_factory=ProviderConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    resilience: ResilienceConfig = field(default_factory=ResilienceConfig)
    features: FeatureFlags = field(default_factory=FeatureFlags)
    content: ContentConfig = field(default_factory=ContentConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)

    def validate(self) -> list[str]:
        """Validate configuration and return list of warnings."""
        warnings = []

        if not self.livekit.is_configured:
            warnings.append("LiveKit credentials not configured (LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)")

        if not self.providers.GOOGLE_API_KEY and self.providers.PRIMARY_LLM == "gemini":
            warnings.append("GOOGLE_API_KEY not set but Gemini is primary LLM")

        if not self.providers.OPENAI_API_KEY and self.providers.PRIMARY_TTS == "openai":
            warnings.append("OPENAI_API_KEY not set but OpenAI is primary TTS")

        if not self.providers.SARVAM_API_KEY and self.providers.PRIMARY_STT == "sarvam":
            warnings.append("SARVAM_API_KEY not set but Sarvam is primary STT")

        if self.features.ENABLE_DATABASE and not self.database.is_configured:
            warnings.append("Database features enabled but Supabase not configured")

        if self.env.is_production:
            if "*" in str(self.security.ALLOWED_ORIGINS):
                warnings.append("CORS allows all origins in production — this is insecure")
            if not self.security.AUTH_SECRET:
                warnings.append("AUTH_SECRET not set in production")

    def __getattr__(self, name: str) -> Any:
        """Allow direct access to child configs for backward compatibility (e.g. config.SERVER_NAME)."""
        sub_configs = (
            self.server,
            self.env,
            self.livekit,
            self.providers,
            self.database,
            self.security,
            self.resilience,
            self.features,
            self.content,
            self.memory,
        )
        for sub in sub_configs:
            if hasattr(sub, name):
                return getattr(sub, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


# Singleton config instance
config = FridayConfig()
