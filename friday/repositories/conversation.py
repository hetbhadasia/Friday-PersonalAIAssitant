"""
F.R.I.D.A.Y. V2 — Conversation History Repository
==================================================
Stores conversation sessions and message logs with Supabase + local JSON fallback.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Optional, Any
from pathlib import Path

from friday.config import config
from friday.core.logging import get_logger

logger = get_logger("conversation_repo")

LOCAL_STORAGE_DIR = Path(".friday_data")
CONV_FILE = LOCAL_STORAGE_DIR / "conversations.json"


class ConversationRepository:
    def __init__(self):
        self._conversations: list[dict[str, Any]] = []
        self._ensure_local_storage()

    def _ensure_local_storage(self):
        try:
            LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            if CONV_FILE.exists():
                with open(CONV_FILE, "r", encoding="utf-8") as f:
                    self._conversations = json.load(f)
        except Exception as exc:
            logger.warning("Could not read local conversations file: %s", exc)

    def _save_local_storage(self):
        try:
            LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONV_FILE, "w", encoding="utf-8") as f:
                json.dump(self._conversations[-200:], f, indent=2, default=str)
        except Exception as exc:
            logger.warning("Could not write local conversations file: %s", exc)

    async def log_message(
        self,
        sender: str,
        content: str,
        tool_calls: list[dict] | None = None,
        room_name: str = "friday-lab",
        user_id: str = "default_user",
    ) -> dict[str, Any]:
        """Record a chat or voice message."""
        record = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "room_name": room_name,
            "sender": sender,
            "content": content,
            "tool_calls": tool_calls or [],
            "created_at": datetime.utcnow().isoformat(),
        }

        if config.features.ENABLE_DATABASE and config.database.is_configured:
            try:
                from friday.services.database import _get_client
                client = _get_client()
                client.table("messages").insert(record).execute()
            except Exception as exc:
                logger.debug("Supabase message log skipped: %s", exc)

        self._conversations.append(record)
        self._save_local_storage()
        return record

    async def get_recent_history(self, limit: int = 10, room_name: str | None = None) -> list[dict[str, Any]]:
        """Get recent messages."""
        if room_name:
            filtered = [m for m in self._conversations if m.get("room_name") == room_name]
        else:
            filtered = self._conversations
        return filtered[-limit:]


conversation_repo = ConversationRepository()
