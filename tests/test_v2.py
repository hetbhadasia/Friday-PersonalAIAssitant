"""
Unit tests for F.R.I.D.A.Y. V2
==============================
"""

import pytest
import asyncio
from friday.config import config
from friday.utils.network import validate_url, sanitize_search_query
from friday.core.permissions import get_tool_permission, ToolPermissionLevel, requires_confirmation
from friday.core.confirmations import ActionConfirmationManager
from friday.core.health import health_checker
from friday.repositories.memory import memory_repo
from friday.repositories.task import task_repo


def test_config_backward_compatibility():
    assert config.SERVER_NAME == "Friday"
    assert config.mcp_server_url == "http://127.0.0.1:8000/sse"
    assert config.server.MCP_SERVER_PORT == 8000
    assert hasattr(config.providers, "PRIMARY_STT")


def test_url_validation():
    valid, _ = validate_url("https://example.com")
    assert valid is True

    valid_http, _ = validate_url("http://github.com/livekit")
    assert valid_http is True

    invalid_scheme, reason = validate_url("file:///etc/passwd")
    assert invalid_scheme is False
    assert "Invalid scheme" in reason

    invalid_empty, _ = validate_url("")
    assert invalid_empty is False


def test_search_query_sanitizer():
    sanitized = sanitize_search_query("  What is quantum computing?!@#$%^&*()  ")
    assert "quantum computing" in sanitized
    assert len(sanitized) > 0


def test_tool_permissions():
    assert get_tool_permission("get_world_news") == ToolPermissionLevel.READ_ONLY
    assert get_tool_permission("remember") == ToolPermissionLevel.USER_DATA
    assert get_tool_permission("delete_task") == ToolPermissionLevel.ACTION
    assert requires_confirmation("delete_task") is True
    assert requires_confirmation("search_web") is False


def test_confirmation_manager():
    mgr = ActionConfirmationManager(expiry_minutes=5)
    action = mgr.request_confirmation("delete_task", "Delete task #1", {"task_id": "task_1"})
    assert action.action_id.startswith("action_")
    assert not action.is_expired

    confirmed = mgr.confirm(action.action_id)
    assert confirmed is not None
    assert confirmed.confirmed is True


@pytest.mark.asyncio
async def test_memory_repo():
    saved = await memory_repo.save_memory("test_key", "test_val", category="test")
    assert saved["key"] == "test_key"
    assert saved["value"] == "test_val"

    retrieved = await memory_repo.get_memory("test_key")
    assert retrieved is not None
    assert retrieved["value"] == "test_val"

    deleted = await memory_repo.delete_memory("test_key")
    assert deleted is True


@pytest.mark.asyncio
async def test_task_repo():
    task = await task_repo.create_task("Test Arc Reactor", priority="high")
    assert task["title"] == "Test Arc Reactor"
    assert task["status"] == "pending"

    updated = await task_repo.update_task(task["id"], status="completed")
    assert updated is not None
    assert updated["status"] == "completed"

    deleted = await task_repo.delete_task(task["id"])
    assert deleted is True


def test_health_checker():
    report = health_checker.check_all()
    assert report.status in ("healthy", "degraded", "unhealthy")
    assert report.uptime_seconds >= 0
    assert len(report.services) > 0
