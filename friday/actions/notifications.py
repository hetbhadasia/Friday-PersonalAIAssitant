"""
F.R.I.D.A.Y. V3 — Notification System & Delivery Adapters
=========================================================
Delivers transactional event alerts (SMS, Email, Push) without exposing credentials.
"""

from abc import ABC, abstractmethod
from typing import Any
from datetime import datetime
from friday.core.logging import get_logger

logger = get_logger("notifications")


class NotificationAdapter(ABC):
    @abstractmethod
    async def send(self, recipient: str, subject: str, message: str, metadata: dict[str, Any]) -> bool:
        pass


class ConsoleNotificationAdapter(NotificationAdapter):
    """Console/Log dispatcher for development and local testing."""

    async def send(self, recipient: str, subject: str, message: str, metadata: dict[str, Any]) -> bool:
        logger.info("[ALERT TO: %s] | Subject: %s | %s", recipient, subject, message)
        return True


class NotificationService:
    def __init__(self):
        self.adapter: NotificationAdapter = ConsoleNotificationAdapter()

    async def dispatch_event(
        self, event_type: str, recipient: str, order_id: str, title: str, details: str = ""
    ) -> bool:
        """Dispatch a transactional notification cleanly without leaking secrets."""
        subject = f"F.R.I.D.A.Y. Alert: {event_type.replace('_', ' ').title()} - {order_id}"
        body = f"{title}\n{details}\nTimestamp: {datetime.utcnow().isoformat()}"
        return await self.adapter.send(recipient, subject, body, {"order_id": order_id, "event_type": event_type})


notification_service = NotificationService()
