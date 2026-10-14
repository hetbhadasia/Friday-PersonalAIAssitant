"""
F.R.I.D.A.Y. V2 — Task Management MCP Tools
===========================================
Allows FRIDAY to create, organize, complete, and track tasks and to-do lists.
"""

from typing import Optional
from friday.repositories.task import task_repo
from friday.core.logging import get_logger

logger = get_logger("task_tools")


def register(mcp):
    @mcp.tool()
    async def create_task(title: str, description: str = "", priority: str = "medium", due_date: str = "") -> str:
        """
        Create a new task or action item.
        - title: Short title of the task
        - description: Additional details or sub-steps
        - priority: 'low', 'medium', 'high', or 'critical'
        - due_date: Optional due date/time string
        """
        try:
            task = await task_repo.create_task(
                title=title,
                description=description,
                priority=priority,
                due_date=due_date or None,
            )
            return f"Task #{task['id']} logged: '{title}' [{priority.upper()} priority]. Standing by."
        except Exception as exc:
            logger.error("Error creating task: %s", exc)
            return f"Error logging task: {exc}"

    @mcp.tool()
    async def list_tasks(status: str = "all") -> str:
        """
        List current tasks.
        - status: 'all', 'pending', 'in_progress', 'completed'
        """
        try:
            tasks = await task_repo.list_tasks(status=status if status != "all" else None)
            if not tasks:
                return f"No tasks found with status '{status}', boss. Clean slate."

            lines = [f"### Current Tasks ({status.upper()})\n"]
            for t in tasks:
                status_icon = "✅" if t.get("status") == "completed" else "⏳"
                prio = t.get("priority", "medium").upper()
                due = f" (Due: {t.get('due_date')})" if t.get("due_date") else ""
                lines.append(f"{status_icon} **#{t['id']}** [{prio}]: {t['title']}{due}")
                if t.get("description"):
                    lines.append(f"   ↳ {t['description']}")
            return "\n".join(lines)
        except Exception as exc:
            logger.error("Error listing tasks: %s", exc)
            return f"Error retrieving tasks: {exc}"

    @mcp.tool()
    async def complete_task(task_id: str) -> str:
        """
        Mark a task as completed.
        - task_id: The ID of the task (e.g. 'task_1')
        """
        try:
            updated = await task_repo.update_task(task_id=task_id, status="completed")
            if updated:
                return f"Marked task #{task_id} ('{updated.get('title')}') as completed, boss. Well done."
            return f"I couldn't locate task #{task_id}."
        except Exception as exc:
            logger.error("Error completing task: %s", exc)
            return f"Error completing task: {exc}"

    @mcp.tool()
    async def update_task(task_id: str, title: str = "", description: str = "", priority: str = "", status: str = "") -> str:
        """
        Update an existing task's title, description, priority, or status.
        """
        try:
            kwargs = {}
            if title:
                kwargs["title"] = title
            if description:
                kwargs["description"] = description
            if priority:
                kwargs["priority"] = priority
            if status:
                kwargs["status"] = status

            updated = await task_repo.update_task(task_id=task_id, **kwargs)
            if updated:
                return f"Task #{task_id} updated successfully."
            return f"Task #{task_id} not found."
        except Exception as exc:
            logger.error("Error updating task: %s", exc)
            return f"Error updating task: {exc}"

    @mcp.tool()
    async def delete_task(task_id: str) -> str:
        """
        Delete a task permanently.
        - task_id: The ID of the task to delete (e.g. 'task_1')
        """
        try:
            deleted = await task_repo.delete_task(task_id=task_id)
            if deleted:
                return f"Task #{task_id} removed from the backlog, boss."
            return f"Task #{task_id} not found."
        except Exception as exc:
            logger.error("Error deleting task: %s", exc)
            return f"Error deleting task: {exc}"
