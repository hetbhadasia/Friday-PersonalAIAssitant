"""
F.R.I.D.A.Y. V2 — Memory MCP Tools
==================================
Allows FRIDAY to store, retrieve, search, and manage long-term facts and session context.
"""

from friday.services.memory import memory_service
from friday.repositories.conversation import conversation_repo
from friday.core.logging import get_logger

logger = get_logger("memory_tools")


def register(mcp):
    @mcp.tool()
    async def remember(key: str, value: str, category: str = "general") -> str:
        """
        Store a permanent piece of information or preference about the user or project.
        Examples:
        - key: 'favorite_coffee', value: 'Double espresso with oat milk'
        - key: 'project_deadline', value: 'Friday at 5 PM'
        - key: 'dog_name', value: 'Barnaby'
        """
        try:
            return await memory_service.remember(key=key, value=value, category=category)
        except Exception as exc:
            logger.error("Error storing memory: %s", exc)
            return f"I had a glitch storing that memory, boss: {exc}"

    @mcp.tool()
    async def recall(query: str = "") -> str:
        """
        Recall stored information, notes, or user preferences.
        If query is empty, lists all key memories in the database.
        """
        try:
            return await memory_service.recall(query=query)
        except Exception as exc:
            logger.error("Error recalling memory: %s", exc)
            return f"Unable to access memory archives right now: {exc}"

    @mcp.tool()
    async def forget(key: str) -> str:
        """Remove a piece of information from memory by key."""
        try:
            return await memory_service.forget(key=key)
        except Exception as exc:
            logger.error("Error forgetting memory: %s", exc)
            return f"Failed to delete memory: {exc}"

    @mcp.tool()
    async def clear_session_memory() -> str:
        """Clear the current short-term working context buffer."""
        memory_service.clear_working_context()
        return "Working context cleared. Ready for fresh instructions, boss."

    @mcp.tool()
    async def get_conversation_history(limit: int = 5) -> str:
        """Fetch the most recent turns of conversation logged in the system."""
        try:
            history = await conversation_repo.get_recent_history(limit=limit)
            if not history:
                return "No previous conversation history logged in this session."
            
            lines = ["### Recent Conversation Log\n"]
            for h in history:
                lines.append(f"**[{h.get('sender', 'user').upper()}]**: {h.get('content')}")
            return "\n".join(lines)
        except Exception as exc:
            return f"Could not retrieve conversation logs: {exc}"
