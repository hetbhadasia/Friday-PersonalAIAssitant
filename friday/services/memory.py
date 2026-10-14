"""
F.R.I.D.A.Y. V2 — Memory Service
=================================
Coordinates short-term working memory (in-session buffer) and
long-term semantic memories stored in repositories.
"""

from typing import Optional, Any
from collections import deque

from friday.config import config
from friday.core.logging import get_logger
from friday.repositories.memory import memory_repo

logger = get_logger("memory_service")


class MemoryService:
    def __init__(self):
        # Short-term rolling buffer for current session
        self._working_memory: deque[dict[str, str]] = deque(maxlen=config.memory.CONTEXT_WINDOW_SIZE)

    def add_working_context(self, role: str, content: str):
        """Add a turn to working memory."""
        self._working_memory.append({"role": role, "content": content})

    def get_working_context(self) -> list[dict[str, str]]:
        """Return the current session's working memory turns."""
        return list(self._working_memory)

    def clear_working_context(self):
        """Clear the current session's working memory."""
        self._working_memory.clear()

    async def remember(self, key: str, value: str, category: str = "general", tags: list[str] | None = None) -> str:
        """Store a long-term memory."""
        await memory_repo.save_memory(key=key, value=value, category=category, tags=tags)
        logger.info("Memory saved: key=%s category=%s", key, category)
        return f"Understood, boss. I'll remember that {key} is {value}."

    async def recall(self, query: str = "", category: Optional[str] = None) -> str:
        """Recall stored memories matching the query or category."""
        memories = await memory_repo.list_memories(category=category, query=query, limit=config.memory.MEMORY_RETRIEVAL_LIMIT)
        if not memories:
            return "I don't have any records matching that in my archives, boss."

        formatted = ["### FRIDAY Archive Retrieval\n"]
        for m in memories:
            formatted.append(f"- **{m.get('key')}** ({m.get('category')}): {m.get('value')}")
        return "\n".join(formatted)

    async def forget(self, key: str) -> str:
        """Forget a specific memory key."""
        deleted = await memory_repo.delete_memory(key)
        if deleted:
            return f"Purged '{key}' from my memory records, boss."
        return f"I couldn't locate any record under '{key}'."


memory_service = MemoryService()
