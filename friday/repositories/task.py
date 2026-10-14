"""
F.R.I.D.A.Y. V2 — Task Repository
================================
Hybrid repository for tasks and to-do items.
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

logger = get_logger("task_repo")

LOCAL_STORAGE_DIR = Path(".friday_data")
TASKS_FILE = LOCAL_STORAGE_DIR / "tasks.json"


class TaskRepository:
    def __init__(self):
        self._table_name = "tasks"
        self._in_memory: dict[str, dict[str, Any]] = {}
        self._counter = 0
        self._ensure_local_storage()

    def _ensure_local_storage(self):
        """Load tasks from local storage."""
        try:
            LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            if TASKS_FILE.exists():
                with open(TASKS_FILE, "r", encoding="utf-8") as f:
                    self._in_memory = json.load(f)
                    self._counter = len(self._in_memory)
        except Exception as exc:
            logger.warning("Could not read local tasks file: %s", exc)

    def _save_local_storage(self):
        """Save tasks to local storage."""
        try:
            LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            with open(TASKS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._in_memory, f, indent=2, default=str)
        except Exception as exc:
            logger.warning("Could not write local tasks file: %s", exc)

    async def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        due_date: Optional[str] = None,
        user_id: str = "default_user",
    ) -> dict[str, Any]:
        """Create a new task."""
        self._counter += 1
        task_id = f"task_{self._counter}"
        now = datetime.utcnow().isoformat()

        task_data = {
            "id": task_id,
            "user_id": user_id,
            "title": title.strip(),
            "description": description.strip(),
            "status": "pending",
            "priority": priority.lower(),
            "due_date": due_date,
            "created_at": now,
            "updated_at": now,
        }

        # Supabase if enabled
        if config.features.ENABLE_DATABASE and config.database.is_configured:
            try:
                from friday.services.database import _get_client
                client = _get_client()
                res = client.table(self._table_name).insert(task_data).execute()
                if res.data:
                    return res.data[0]
            except Exception as exc:
                logger.warning("Supabase task creation failed, falling back to local: %s", exc)

        self._in_memory[task_id] = task_data
        self._save_local_storage()
        return task_data

    async def get_task(self, task_id: str) -> Optional[dict[str, Any]]:
        """Fetch task by ID."""
        if config.features.ENABLE_DATABASE and config.database.is_configured:
            try:
                from friday.services.database import _get_client
                client = _get_client()
                res = client.table(self._table_name).select("*").eq("id", task_id).execute()
                if res.data:
                    return res.data[0]
            except Exception as exc:
                logger.warning("Supabase task lookup failed: %s", exc)

        return self._in_memory.get(task_id)

    async def list_tasks(
        self,
        status: Optional[str] = None,
        user_id: str = "default_user",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List tasks with optional status filter."""
        if config.features.ENABLE_DATABASE and config.database.is_configured:
            try:
                from friday.services.database import _get_client
                client = _get_client()
                query = client.table(self._table_name).select("*")
                if status and status != "all":
                    query = query.eq("status", status)
                res = query.order("created_at", desc=True).limit(limit).execute()
                if res.data is not None:
                    return res.data
            except Exception as exc:
                logger.warning("Supabase task list failed, falling back to local: %s", exc)

        results = list(self._in_memory.values())
        if status and status != "all":
            results = [t for t in results if t.get("status") == status]
        return sorted(results, key=lambda x: x.get("created_at", ""), reverse=True)[:limit]

    async def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Update fields of an existing task."""
        now = datetime.utcnow().isoformat()
        updates = {"updated_at": now}
        if title is not None:
            updates["title"] = title
        if description is not None:
            updates["description"] = description
        if status is not None:
            updates["status"] = status
        if priority is not None:
            updates["priority"] = priority

        if config.features.ENABLE_DATABASE and config.database.is_configured:
            try:
                from friday.services.database import _get_client
                client = _get_client()
                res = client.table(self._table_name).update(updates).eq("id", task_id).execute()
                if res.data:
                    return res.data[0]
            except Exception as exc:
                logger.warning("Supabase task update failed: %s", exc)

        if task_id in self._in_memory:
            self._in_memory[task_id].update(updates)
            self._save_local_storage()
            return self._in_memory[task_id]

        return None

    async def delete_task(self, task_id: str) -> bool:
        """Delete task by ID."""
        if config.features.ENABLE_DATABASE and config.database.is_configured:
            try:
                from friday.services.database import _get_client
                client = _get_client()
                client.table(self._table_name).delete().eq("id", task_id).execute()
            except Exception as exc:
                logger.warning("Supabase task delete failed: %s", exc)

        if task_id in self._in_memory:
            del self._in_memory[task_id]
            self._save_local_storage()
            return True
        return False


# Singleton
task_repo = TaskRepository()
