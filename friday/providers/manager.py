"""
F.R.I.D.A.Y. V2 — Resilient Provider Manager
============================================
Handles STT, LLM, and TTS provider instantiation with automatic fallback,
health validation, and failover tracking.
"""

import os
from typing import Tuple, Any

from livekit.agents import llm as lk_llm

from livekit.plugins import google as lk_google, openai as lk_openai, sarvam, silero, groq as lk_groq

from friday.config import config
from friday.core.logging import get_logger
from friday.core.metrics import metrics

logger = get_logger("provider_manager")


def _is_valid_key(key: str | None) -> bool:
    """Check if an API key is present and not a dummy/placeholder string."""
    if not key or not isinstance(key, str):
        return False
    key = key.strip()
    if not key or "xxxx" in key.lower() or "your-" in key.lower() or "you-google" in key.lower():
        return False
    return len(key) > 8


class ProviderManager:
    """Manages AI provider selection, fallback logic, and runtime diagnostics."""

    @classmethod
    def get_stt(cls) -> Any:
        primary = config.providers.PRIMARY_STT.lower()
        fallback = config.providers.FALLBACK_STT.lower()

        # Check primary: Sarvam
        if primary == "sarvam" and _is_valid_key(config.providers.SARVAM_API_KEY):
            logger.info("Initializing Primary STT: Sarvam Saaras v3")
            return sarvam.STT(
                language="unknown",
                model=config.providers.SARVAM_STT_MODEL,
                mode="transcribe",
                flush_signal=True,
                sample_rate=config.providers.SARVAM_STT_SAMPLE_RATE,
            )

        # Fallback to Whisper
        if (primary == "whisper" or fallback == "whisper") and _is_valid_key(config.providers.OPENAI_API_KEY):
            logger.info("Using Whisper STT (%s)", "Primary" if primary == "whisper" else "Fallback")
            if primary != "whisper":
                metrics.record_failover("stt", primary, "whisper")
            return lk_openai.STT(model="whisper-1")

        # If Sarvam key exists even without check
        if config.providers.SARVAM_API_KEY:
            logger.warning("Using Sarvam STT despite key check warning")
            return sarvam.STT(language="unknown", model="saaras:v3", mode="transcribe")

        # Default fallback
        logger.warning("Falling back to OpenAI Whisper STT")
        return lk_openai.STT(model="whisper-1")

   
    @classmethod
    def get_llm(cls) -> Any:
        primary = config.providers.PRIMARY_LLM.lower()
        fallback = config.providers.FALLBACK_LLM.lower()

        providers = {}

        groq_key = config.providers.GROQ_API_KEY or os.getenv("GROQ_API_KEY")
        google_key = config.providers.GOOGLE_API_KEY or os.getenv("GOOGLE_API_KEY")
        openai_key = config.providers.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")

        if _is_valid_key(groq_key):
            providers["groq"] = lk_groq.LLM(
                model=config.providers.GROQ_MODEL,
                api_key=groq_key,
            )

        if _is_valid_key(google_key):
            providers["gemini"] = lk_google.LLM(
                model=config.providers.GEMINI_MODEL,
                api_key=google_key,
            )

        if _is_valid_key(openai_key):
            providers["openai"] = lk_openai.LLM(
                model=config.providers.OPENAI_LLM_MODEL,
                api_key=openai_key,
            )

        order = []
        for name in (primary, fallback, "gemini", "groq", "openai"):
            if name in providers and name not in order:
                order.append(name)

        if not order:
            raise RuntimeError(
                "No valid LLM API key found. Configure Groq, Gemini, or OpenAI in .env."
            )

        selected = [providers[name] for name in order]

        logger.info("LLM fallback order: %s", " -> ".join(order))

        if len(selected) == 1:
            return selected[0]

        return lk_llm.FallbackAdapter(
            selected,
            attempt_timeout=10.0,
            max_retry_per_llm=0,
        )

    @classmethod
    def get_tts(cls) -> Any:
        primary = config.providers.PRIMARY_TTS.lower()
        fallback = config.providers.FALLBACK_TTS.lower()

        # Check OpenAI
        if primary == "openai" and _is_valid_key(config.providers.OPENAI_API_KEY):
            logger.info("Initializing Primary TTS: OpenAI Nova (%s)", config.providers.OPENAI_TTS_VOICE)
            return lk_openai.TTS(
                model=config.providers.OPENAI_TTS_MODEL,
                voice=config.providers.OPENAI_TTS_VOICE,
                speed=config.providers.TTS_SPEED,
            )

        # Fallback to Sarvam Bulbul
        if (primary == "sarvam" or fallback == "sarvam") and _is_valid_key(config.providers.SARVAM_API_KEY):
            logger.info("Using Sarvam TTS (%s)", "Primary" if primary == "sarvam" else "Fallback")
            if primary != "sarvam":
                metrics.record_failover("tts", primary, "sarvam")
            return sarvam.TTS(
                target_language_code=config.providers.SARVAM_TTS_LANGUAGE,
                model=config.providers.SARVAM_TTS_MODEL,
                speaker=config.providers.SARVAM_TTS_SPEAKER,
                pace=config.providers.TTS_SPEED,
                output_audio_codec="mp3",
            )

        # Default to OpenAITTS
        logger.info("Defaulting to OpenAI TTS")
        return lk_openai.TTS(
            model=config.providers.OPENAI_TTS_MODEL,
            voice=config.providers.OPENAI_TTS_VOICE,
            speed=config.providers.TTS_SPEED,
        )
