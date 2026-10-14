"""
F.R.I.D.A.Y. V2 — Action Confirmation Manager
===============================================
Manages confirmation flow for consequential actions.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Any

from friday.core.logging import get_logger

logger = get_logger("confirmations")


@dataclass
class PendingAction:
    """An action awaiting user confirmation."""
    action_id: str
    tool_name: str
    description: str
    parameters: dict
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(minutes=2))
    confirmed: bool = False
    cancelled: bool = False

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at


class ActionConfirmationManager:
    """
    Manages pending confirmations for consequential actions.
    
    Usage:
        manager = ActionConfirmationManager()
        
        # When a tool requires confirmation:
        pending = manager.request_confirmation("delete_task", "Delete task 'Buy groceries'", {"task_id": "123"})
        # → FRIDAY asks: "Shall I go ahead and delete that task, boss?"
        
        # When user confirms:
        action = manager.confirm(pending.action_id)
        # → Execute the action
    """

    def __init__(self, expiry_minutes: int = 2):
        self._pending: dict[str, PendingAction] = {}
        self._expiry_minutes = expiry_minutes
        self._counter = 0

    def _generate_id(self) -> str:
        self._counter += 1
        return f"action_{self._counter}"

    def request_confirmation(
        self,
        tool_name: str,
        description: str,
        parameters: dict | None = None,
    ) -> PendingAction:
        """Create a pending action that requires confirmation."""
        self._cleanup_expired()

        action = PendingAction(
            action_id=self._generate_id(),
            tool_name=tool_name,
            description=description,
            parameters=parameters or {},
            expires_at=datetime.utcnow() + timedelta(minutes=self._expiry_minutes),
        )
        self._pending[action.action_id] = action

        logger.info(
            "Confirmation requested: action=%s tool=%s desc=%s",
            action.action_id, tool_name, description,
        )
        return action

    def confirm(self, action_id: str) -> Optional[PendingAction]:
        """Confirm a pending action. Returns the action if valid, None if expired/missing."""
        self._cleanup_expired()

        action = self._pending.pop(action_id, None)
        if action is None:
            logger.warning("Confirmation for unknown/expired action: %s", action_id)
            return None

        if action.is_expired:
            logger.warning("Confirmation expired: %s", action_id)
            return None

        action.confirmed = True
        logger.info("Action confirmed: %s (%s)", action_id, action.tool_name)
        return action

    def cancel(self, action_id: str) -> bool:
        """Cancel a pending action."""
        action = self._pending.pop(action_id, None)
        if action:
            action.cancelled = True
            logger.info("Action cancelled: %s", action_id)
            return True
        return False

    def get_pending(self, user_id: str | None = None) -> list[PendingAction]:
        """Get all pending (non-expired) actions."""
        self._cleanup_expired()
        return list(self._pending.values())

    def cancel_all(self):
        """Cancel all pending actions."""
        count = len(self._pending)
        self._pending.clear()
        if count:
            logger.info("Cancelled %d pending actions", count)

    def _cleanup_expired(self):
        """Remove expired pending actions."""
        expired = [aid for aid, a in self._pending.items() if a.is_expired]
        for aid in expired:
            del self._pending[aid]


# Singleton
confirmation_manager = ActionConfirmationManager()
