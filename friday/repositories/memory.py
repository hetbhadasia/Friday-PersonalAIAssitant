"""
F.R.I.D.A.Y. V2 — Memory Repository
===================================
Hybrid repository for long-term user memories.
Uses Supabase if available; otherwise falls back to a resilient local JSON/in-memory store.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Optional, Any
from pathlib import Path

from friday.config import config
from friday.core.logging import get_logger
from friday.core.errors import DatabaseError

logger = get_logger("memory_repo")

LOCAL_STORAGE_DIR = Path(".friday_data")
MEMORIES_FILE = LOCAL_STORAGE_DIR / "memories.json"


class MemoryRepository:
    def __init__(self):
        self._table_name = "memories"
        self._in_memory: dict[str, dict[str, Any]] = {}
        self._ensure_local_storage()

    def _ensure_local_storage(self):
        """Load memories from local JSON file if Supabase is offline or unconfigured."""
        try:
            LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            if MEMORIES_FILE.exists():
                with open(MEMORIES_FILE, "r", encoding="utf-8") as f:
                    self._in_memory = json.load(f)
        except Exception as exc:
            logger.warning("Could not read local memories file: %s", exc)

    def _save_local_storage(self):
        """Save in-memory state to local JSON file."""
        try:
            LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            with open(MEMORIES_FILE, "w", encoding="utf-8") as f:
                json.dump(self._in_memory, f, indent=2, default=str)
        except Exception as exc:
            logger.warning("Could not write local memories file: %s", exc)

    async def save_memory(
        self,
        key: str,
        value: str,
        category: str = "general",
        user_id: str = "default_user",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Save or update a memory."""
        tags = tags or []
        now = datetime.utcnow().isoformat()

        # Try Supabase if configured
        if config.features.ENABLE_DATABASE and config.database.is_configured:
            try:
                from friday.services.database import _get_client
                client = _get_client()
                data = {
                    "user_id": user_id,
                    "key": key,
                    "value": value,
                    "category": category,
                    "tags": tags,
                    "updated_at": now,
                }
                # Check if exists
                existing = client.table(self._table_name).select("id").eq("key", key).execute()
                if existing.data:
                    res = client.table(self._table_name).update(data).eq("key", key).execute()
                    return res.data[0]
                else:
                    data["created_at"] = now
                    res = client.table(self._table_name).insert(data).execute()
                    return res.data[0]
            except Exception as exc:
                logger.warning("Supabase memory save failed, falling back to local: %s", exc)

        # Fallback local store
        record_id = self._in_memory.get(key, {}).get("id", str(uuid.uuid4()))
        created_at = self._in_memory.get(key, {}).get("created_at", now)
        record = {
            "id": record_id,
            "user_id": user_id,
            "key": key,
            "value": value,
            "category": category,
            "tags": tags,
            "created_at": created_at,
            "updated_at": now,
        }
        self._in_memory[key] = record
        self._save_local_storage()
        return record

    async def get_memory(self, key: str, user_id: str = "default_user") -> Optional[dict[str, Any]]:
        """Retrieve a specific memory by key."""
        if config.features.ENABLE_DATABASE and config.database.is_configured:
            try:
                from friday.services.database import _get_client
                client = _get_client()
                res = client.table(self._table_name).select("*").eq("key", key).execute()
                if res.data:
                    return res.data[0]
            except Exception as exc:
                logger.warning("Supabase memory get failed, falling back to local: %s", exc)

        return self._in_memory.get(key)

    async def list_memories(
        self,
        category: Optional[str] = None,
        query: Optional[str] = None,
        user_id: str = "default_user",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List memories with optional category filter and text search."""
        if config.features.ENABLE_DATABASE and config.database.is_configured:
            try:
                from friday.services.database import _get_client
                client = _get_client()
                query_builder = client.table(self._table_name).select("*")
                if category:
                    query_builder = query_builder.eq("category", category)
                if query:
                    query_builder = query_builder.ilike("value", f"%{query}%")
                res = query_builder.limit(limit).execute()
                if res.data is not None:
                    return res.data
            except Exception as exc:
                logger.warning("Supabase memory list failed, falling back to local: %s", exc)

        # Local search
        results = []
        for mem in self._in_memory.values():
            if category and mem.get("category") != category:
                continue
            if query:
                q = query.lower()
                if q not in mem.get("key", "").lower() and q not in mem.get("value", "").lower():
                    continue
            results.append(mem)
        return results[:limit]

    async def delete_memory(self, key: str, user_id: str = "default_user") -> bool:
        """Delete a memory by key."""
        if config.features.ENABLE_DATABASE and config.database.is_configured:
            try:
                from friday.services.database import _get_client
                client = _get_client()
                client.table(self._table_name).delete().eq("key", key).execute()
            except Exception as exc:
                logger.warning("Supabase memory delete failed: %s", exc)

        if key in self._in_memory:
            del self._in_memory[key]
            self._save_local_storage()
            return True
        return False

    async def clear_all(self, user_id: str = "default_user") -> int:
        """Clear all memories."""
        count = len(self._in_memory)
        self._in_memory.clear()
        self._save_local_storage()
        return count


# Singleton
memory_repo = MemoryRepository()
