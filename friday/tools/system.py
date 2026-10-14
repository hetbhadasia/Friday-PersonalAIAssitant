"""
System tools — time, environment info, shell commands, etc.
"""

import datetime
import platform


def register(mcp):

    @mcp.tool()
    def get_current_time() -> str:
        """Return the current date and time in India Standard Time."""
        from zoneinfo import ZoneInfo

        now = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
        return now.strftime("It is %I:%M %p on %A, %d %B %Y IST.")

    @mcp.tool()
    def get_system_info() -> dict:
        """Return basic information about the host system."""
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
        }
