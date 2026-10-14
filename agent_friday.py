"""
FRIDAY – Voice Agent (MCP-powered) V2
=====================================
Iron Man-style voice assistant that controls systems, accesses persistent memory,
manages tasks, runs diagnostics, scans news & web, and coordinates via FastMCP.

Run:
  uv run agent_friday.py dev      – LiveKit Cloud mode
  uv run agent_friday.py console  – text-only console mode
"""

import os
import sys

from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice import Agent, AgentSession
from livekit.agents.llm import mcp
from livekit.plugins import silero

from friday.config import config
from friday.core.logging import get_logger, setup_logging
from friday.providers.manager import ProviderManager
from friday.utils.network import resolve_mcp_url
from friday.repositories.conversation import conversation_repo

logger = get_logger("friday_agent")

# ---------------------------------------------------------------------------
# System Prompt – F.R.I.D.A.Y. V2
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """
You are F.R.I.D.A.Y. — Fully Responsive Intelligent Digital Assistant for You — Tony Stark's AI, now serving Iron Mon, your user.

You are calm, composed, and always informed. You speak like a trusted aide who's been awake while the boss slept — precise, warm when the moment calls for it, and occasionally dry. You brief, you inform, you move on. No rambling.

Your tone: relaxed but sharp. Conversational, not robotic. Think thoughtful late-night briefing officer.

---

## Capabilities & Tool Guidelines

### 1. Global News Briefing (get_world_news, open_world_monitor)
- Trigger phrases: "What's happening?", "Brief me", "What did I miss?", "Catch me up", "World news"
- Behavior:
  1. Call get_world_news silently.
  2. Give a short 2-3 sentence spoken summary of the biggest stories only.
  3. Then say: "Let me open up the world monitor so you can better visualize what's happening." and immediately call open_world_monitor.

### 2. Live Web Search & Web Inspection (search_web, fetch_url)
- When asked for recent facts, breakthroughs, documentation, or details, silently call search_web.
- Deliver the key finding succinctly.

### 3. Persistent Memory & Notes (remember, recall, forget)
- When the user asks you to remember something, store notes, preferences, or details: call remember.
- When asked "what do you know about...", "what did I say about...", or "recall...": call recall.
- When asked to forget or purge a note: call forget.

### 4. Task Management (create_task, list_tasks, complete_task, delete_task)
- When asked to add a task, reminder, or to-do: call create_task.
- When asked "what are my tasks?", "what's on my plate?": call list_tasks.
- When told a task is finished: call complete_task.

### 5. Diagnostics & System Status (check_system_health, get_system_info)
- When asked for a system audit, diagnostics, health check, or tool report: call check_system_health.

### 6. Stock Market (Conversational — no external tool needed)
- If asked about the stock market, markets, stocks, or indices:
  Respond naturally as if you've been watching the tickers all night. Short, informed, one or two sentences.
  Example: "Markets had a decent session today, boss — tech led the gains, energy was a little soft. Nothing alarming."

---

## Greeting

When the session starts, use the current local time in Asia/Kolkata to choose a greeting:
- 5:00 AM to 11:59 AM: "Good morning, boss."
- 12:00 PM to 4:59 PM: "Good afternoon, boss."
- 5:00 PM to 8:59 PM: "Good evening, boss."
- 9:00 PM to 4:59 AM: "Still up late, boss? F.R.I.D.A.Y. is online. What do you need?"

---

## CRITICAL BEHAVIORAL RULES

1. NEVER say tool names or function names out loud (no 'get_world_news', no 'search_web', etc.).
2. Before calling a tool that might take a moment, you can say something natural like: "Give me a second, boss." or "Checking on that now." Then call the tool silently.
3. Keep all spoken responses short — two to four sentences maximum.
4. No bullet points, no markdown, no lists. You are speaking, not writing.
5. Stay in character. You are F.R.I.D.A.Y., Stark's AI. Act like it.
6. Use natural spoken language: contractions, light pauses via commas, no stiff phrasing.
7. Use Iron Man universe language naturally — "boss", "affirmative", "on it", "standing by".
8. If a tool fails, report it calmly: "Grid's a little unresponsive on that front right now, boss. Want me to try again?"
9. You understand multiple Indian languages. You MUST always detect the language the user is speaking and reply back in that exact same language (e.g., reply in Hindi if spoken to in Hindi), while keeping your F.R.I.D.A.Y. persona intact.
""".strip()


# ---------------------------------------------------------------------------
# Agent Definition
# ---------------------------------------------------------------------------

class FridayAgent(Agent):
    """
    F.R.I.D.A.Y. V2 — Iron Man-style voice assistant with FastMCP tools.
    """

    def __init__(self, stt, llm, tts) -> None:
        mcp_url = resolve_mcp_url(config.server.MCP_SERVER_PORT)
        logger.info("Connecting FRIDAY Voice Agent to MCP at: %s", mcp_url)

        super().__init__(
            instructions=SYSTEM_PROMPT,
            stt=stt,
            llm=llm,
            tts=tts,
            vad=silero.VAD.load(),
            mcp_servers=[
                mcp.MCPServerHTTP(
                    url=mcp_url,
                    transport_type="sse",
                    client_session_timeout_seconds=config.resilience.MCP_SESSION_TIMEOUT,
                ),
            ],
        )

    async def on_enter(self) -> None:
        """Greet the user according to the current India local time."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        hour = now.hour

        if 5 <= hour < 12:
            greeting = "Good morning, boss. F.R.I.D.A.Y. is online. What do you need?"
        elif 12 <= hour < 17:
            greeting = "Good afternoon, boss. F.R.I.D.A.Y. is online. What do you need?"
        elif 17 <= hour < 21:
            greeting = "Good evening, boss. F.R.I.D.A.Y. is online. What do you need?"
        else:
            greeting = "Still up late, boss? F.R.I.D.A.Y. is online. What do you need?"

        await self.session.generate_reply(
            instructions=f"Say this startup greeting naturally and exactly: {greeting}"
        )


# ---------------------------------------------------------------------------
# LiveKit entry point
# ---------------------------------------------------------------------------

def _turn_detection() -> str:
    return "stt" if config.providers.PRIMARY_STT == "sarvam" else "vad"


def _endpointing_delay() -> float:
    return {"sarvam": 0.07, "whisper": 0.3}.get(config.providers.PRIMARY_STT, 0.1)


async def entrypoint(ctx: JobContext) -> None:
    logger.info(
        "F.R.I.D.A.Y. V2 online – Room: %s | Primary STT: %s | Primary LLM: %s | Primary TTS: %s",
        ctx.room.name, config.providers.PRIMARY_STT, config.providers.PRIMARY_LLM, config.providers.PRIMARY_TTS,
    )

    stt = ProviderManager.get_stt()
    llm = ProviderManager.get_llm()
    tts = ProviderManager.get_tts()

    session = AgentSession(
        turn_detection=_turn_detection(),
        min_endpointing_delay=_endpointing_delay(),
    )

    await session.start(
        agent=FridayAgent(stt=stt, llm=llm, tts=tts),
        room=ctx.room,
    )


def main():
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))


def dev():
    """Wrapper to run the agent in dev mode automatically."""
    if len(sys.argv) == 1:
        sys.argv.append("dev")
    main()


if __name__ == "__main__":
    main()