"""
Standalone Unit Test Runner for F.R.I.D.A.Y. V2
================================================
Uses Python's standard unittest and asyncio (no external test dependencies required).
"""

import unittest
import asyncio
from friday.config import config
from friday.utils.network import validate_url, sanitize_search_query
from friday.core.permissions import get_tool_permission, ToolPermissionLevel, requires_confirmation
from friday.core.confirmations import ActionConfirmationManager
from friday.core.health import health_checker
from friday.repositories.memory import memory_repo
from friday.repositories.task import task_repo


class TestFridayV2(unittest.TestCase):

    def test_config_backward_compatibility(self):
        self.assertEqual(config.SERVER_NAME, "Friday")
        self.assertEqual(config.mcp_server_url, "http://127.0.0.1:8000/sse")
        self.assertEqual(config.server.MCP_SERVER_PORT, 8000)
        self.assertTrue(hasattr(config.providers, "PRIMARY_STT"))

    def test_url_validation(self):
        valid, _ = validate_url("https://example.com")
        self.assertTrue(valid)

        valid_http, _ = validate_url("http://github.com/livekit")
        self.assertTrue(valid_http)

        invalid_scheme, reason = validate_url("file:///etc/passwd")
        self.assertFalse(invalid_scheme)
        self.assertIn("not allowed", reason)

        invalid_empty, _ = validate_url("")
        self.assertFalse(invalid_empty)

    def test_search_query_sanitizer(self):
        sanitized = sanitize_search_query("  What is quantum computing?!@#$%^&*()  ")
        self.assertIn("quantum computing", sanitized)
        self.assertTrue(len(sanitized) > 0)

    def test_tool_permissions(self):
        self.assertEqual(get_tool_permission("get_world_news"), ToolPermissionLevel.READ_ONLY)
        self.assertEqual(get_tool_permission("remember"), ToolPermissionLevel.USER_DATA)
        self.assertEqual(get_tool_permission("delete_task"), ToolPermissionLevel.ACTION)
        self.assertTrue(requires_confirmation("delete_task"))
        self.assertFalse(requires_confirmation("search_web"))

    def test_confirmation_manager(self):
        mgr = ActionConfirmationManager(expiry_minutes=5)
        action = mgr.request_confirmation("delete_task", "Delete task #1", {"task_id": "task_1"})
        self.assertTrue(action.action_id.startswith("action_"))
        self.assertFalse(action.is_expired)

        confirmed = mgr.confirm(action.action_id)
        self.assertIsNotNone(confirmed)
        self.assertTrue(confirmed.confirmed)

    def test_memory_repo(self):
        async def _run():
            saved = await memory_repo.save_memory("mark_85_key", "Mark 85 armor specs", category="suits")
            self.assertEqual(saved["key"], "mark_85_key")
            self.assertEqual(saved["value"], "Mark 85 armor specs")

            retrieved = await memory_repo.get_memory("mark_85_key")
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved["value"], "Mark 85 armor specs")

            deleted = await memory_repo.delete_memory("mark_85_key")
            self.assertTrue(deleted)
        asyncio.run(_run())

    def test_task_repo(self):
        async def _run():
            task = await task_repo.create_task("Test Arc Reactor Power", priority="high")
            self.assertEqual(task["title"], "Test Arc Reactor Power")
            self.assertEqual(task["status"], "pending")

            updated = await task_repo.update_task(task["id"], status="completed")
            self.assertIsNotNone(updated)
            self.assertEqual(updated["status"], "completed")

            deleted = await task_repo.delete_task(task["id"])
            self.assertTrue(deleted)
        asyncio.run(_run())

    def test_health_checker(self):
        report = health_checker.check_all()
        self.assertIn(report.status, ("healthy", "degraded", "unhealthy"))
        self.assertGreaterEqual(report.uptime_seconds, 0)
        self.assertGreater(len(report.services), 0)


if __name__ == "__main__":
    unittest.main()
