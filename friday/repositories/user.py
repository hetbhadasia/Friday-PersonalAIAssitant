"""
F.R.I.D.A.Y. V2 — User & Preferences Repository
================================================
Manages user profiles, preferences (e.g. language, title, custom greetings).
"""

import json
from datetime import datetime
from typing import Optional, Any
from pathlib import Path

from friday.config import config
from friday.core.logging import get_logger

logger = get_logger("user_repo")

LOCAL_STORAGE_DIR = Path(".friday_data")
USER_FILE = LOCAL_STORAGE_DIR / "user_preferences.json"


class UserRepository:
    def __init__(self):
        self._user_data: dict[str, Any] = {
            "identity": "iron-man",
            "display_name": "Tony Stark",
            "title": "boss",
            "preferred_language": "en",
            "theme": "iron-man-gold",
            "notifications_enabled": True,
            "created_at": datetime.utcnow().isoformat(),
        }
        self._ensure_local_storage()

    def _ensure_local_storage(self):
        try:
            LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            if USER_FILE.exists():
                with open(USER_FILE, "r", encoding="utf-8") as f:
                    self._user_data = json.load(f)
        except Exception as exc:
            logger.warning("Could not read local user preferences: %s", exc)

    def _save_local_storage(self):
        try:
            LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            with open(USER_FILE, "w", encoding="utf-8") as f:
                json.dump(self._user_data, f, indent=2, default=str)
        except Exception as exc:
            logger.warning("Could not write local user preferences: %s", exc)

    async def get_preferences(self, user_id: str = "default_user") -> dict[str, Any]:
        return dict(self._user_data)

    async def update_preferences(self, updates: dict[str, Any], user_id: str = "default_user") -> dict[str, Any]:
        self._user_data.update(updates)
        self._user_data["updated_at"] = datetime.utcnow().isoformat()
        self._save_local_storage()
        return dict(self._user_data)


user_repo = UserRepository()
