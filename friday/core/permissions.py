"""
F.R.I.D.A.Y. V2 — Tool Permissions
===================================
Permission levels for MCP tools and enforcement logic.
"""

from enum import Enum
from typing import Optional
from friday.core.errors import ToolPermissionError, AuthorizationError
from friday.core.logging import get_logger

logger = get_logger("permissions")


class ToolPermissionLevel(Enum):
    """Permission categories for MCP tools."""
    READ_ONLY = "read_only"         # Informational: time, news, search, system info
    USER_DATA = "user_data"         # Personal: memory, conversations, tasks, preferences
    ACTION = "action"               # Consequential: send email, create ticket, modify files


# ---------------------------------------------------------------------------
# Tool → Permission mapping
# ---------------------------------------------------------------------------

TOOL_PERMISSIONS: dict[str, ToolPermissionLevel] = {
    # READ_ONLY — safe, no side effects
    "get_world_news": ToolPermissionLevel.READ_ONLY,
    "search_web": ToolPermissionLevel.READ_ONLY,
    "fetch_url": ToolPermissionLevel.READ_ONLY,
    "get_current_time": ToolPermissionLevel.READ_ONLY,
    "get_system_info": ToolPermissionLevel.READ_ONLY,
    "format_json": ToolPermissionLevel.READ_ONLY,
    "word_count": ToolPermissionLevel.READ_ONLY,
    "check_health": ToolPermissionLevel.READ_ONLY,

    # USER_DATA — reads/writes personal data
    "remember": ToolPermissionLevel.USER_DATA,
    "recall": ToolPermissionLevel.USER_DATA,
    "forget": ToolPermissionLevel.USER_DATA,
    "get_conversation_history": ToolPermissionLevel.USER_DATA,
    "list_tasks": ToolPermissionLevel.USER_DATA,
    "get_task": ToolPermissionLevel.USER_DATA,
    "get_user_preferences": ToolPermissionLevel.USER_DATA,
    "update_user_preferences": ToolPermissionLevel.USER_DATA,

    # ACTION — requires confirmation for consequential operations
    "create_task": ToolPermissionLevel.USER_DATA,
    "complete_task": ToolPermissionLevel.USER_DATA,
    "delete_task": ToolPermissionLevel.ACTION,
    "open_world_monitor": ToolPermissionLevel.ACTION,
    "clear_session_memory": ToolPermissionLevel.ACTION,
}


def get_tool_permission(tool_name: str) -> ToolPermissionLevel:
    """Get the permission level for a tool. Defaults to READ_ONLY for unknown tools."""
    return TOOL_PERMISSIONS.get(tool_name, ToolPermissionLevel.READ_ONLY)


def check_tool_permission(
    tool_name: str,
    user_id: Optional[str] = None,
    max_level: ToolPermissionLevel = ToolPermissionLevel.ACTION,
) -> bool:
    """
    Check if a tool is allowed at the given maximum permission level.
    
    Returns True if allowed, raises ToolPermissionError otherwise.
    """
    required = get_tool_permission(tool_name)

    level_order = [
        ToolPermissionLevel.READ_ONLY,
        ToolPermissionLevel.USER_DATA,
        ToolPermissionLevel.ACTION,
    ]

    if level_order.index(required) > level_order.index(max_level):
        logger.warning(
            "Permission denied: tool=%s requires=%s max_allowed=%s user=%s",
            tool_name, required.value, max_level.value, user_id,
        )
        raise ToolPermissionError(
            tool=tool_name,
            required_level=required.value,
        )

    return True


def requires_confirmation(tool_name: str) -> bool:
    """Check if a tool requires user confirmation before execution."""
    return get_tool_permission(tool_name) == ToolPermissionLevel.ACTION
