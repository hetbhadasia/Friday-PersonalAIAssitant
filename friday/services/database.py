"""
F.R.I.D.A.Y. V2 — Database Service
===================================
Supabase connection management and base repository.
"""

import json
from typing import Optional, Any
from datetime import datetime

from friday.config import config
from friday.core.logging import get_logger
from friday.core.errors import DatabaseError, DatabaseNotConfiguredError

logger = get_logger("database")

# Lazy import — supabase may not be installed
_supabase_client = None


def _get_client():
    """Get or create the Supabase client singleton."""
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    if not config.database.is_configured:
        raise DatabaseNotConfiguredError()

    try:
        from supabase import create_client, Client
        _supabase_client = create_client(
            config.database.SUPABASE_URL,
            config.database.SUPABASE_SERVICE_KEY or config.database.SUPABASE_API_KEY,
        )
        logger.info("Supabase client initialized")
        return _supabase_client
    except ImportError:
        raise DatabaseError(
            "supabase package not installed. Run: pip install supabase",
            operation="connect",
        )
    except Exception as exc:
        logger.error("Failed to initialize Supabase: %s", exc)
        raise DatabaseError(f"Supabase connection failed: {exc}", operation="connect")


class BaseRepository:
    """Base repository with common Supabase CRUD operations."""

    def __init__(self, table_name: str):
        self.table_name = table_name

    @property
    def client(self):
        return _get_client()

    @property
    def table(self):
        return self.client.table(self.table_name)

    async def insert(self, data: dict) -> dict | None:
        try:
            result = self.table.insert(data).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as exc:
            logger.error("Insert failed on %s: %s", self.table_name, exc)
            raise DatabaseError(f"Insert failed: {exc}", operation="insert")

    async def get_by_id(self, record_id: str) -> dict | None:
        try:
            result = self.table.select("*").eq("id", record_id).execute()
            return result.data[0] if result.data else None
        except Exception as exc:
            logger.error("Get by ID failed on %s: %s", self.table_name, exc)
            raise DatabaseError(f"Get failed: {exc}", operation="select")

    async def update(self, record_id: str, data: dict) -> dict | None:
        try:
            data["updated_at"] = datetime.utcnow().isoformat()
            result = self.table.update(data).eq("id", record_id).execute()
            return result.data[0] if result.data else None
        except Exception as exc:
            logger.error("Update failed on %s: %s", self.table_name, exc)
            raise DatabaseError(f"Update failed: {exc}", operation="update")

    async def delete(self, record_id: str) -> bool:
        try:
            self.table.delete().eq("id", record_id).execute()
            return True
        except Exception as exc:
            logger.error("Delete failed on %s: %s", self.table_name, exc)
            raise DatabaseError(f"Delete failed: {exc}", operation="delete")

    async def find_by(self, column: str, value: Any, limit: int = 100) -> list[dict]:
        try:
            result = self.table.select("*").eq(column, value).limit(limit).execute()
            return result.data or []
        except Exception as exc:
            logger.error("Find by %s failed on %s: %s", column, self.table_name, exc)
            raise DatabaseError(f"Query failed: {exc}", operation="select")

    async def find_recent(self, column: str, value: Any, order_by: str = "created_at", limit: int = 50) -> list[dict]:
        try:
            result = (
                self.table
                .select("*")
                .eq(column, value)
                .order(order_by, desc=True)
                .limit(limit)
                .execute()
            )
            return result.data or []
        except Exception as exc:
            logger.error("Find recent failed on %s: %s", self.table_name, exc)
            raise DatabaseError(f"Query failed: {exc}", operation="select")
