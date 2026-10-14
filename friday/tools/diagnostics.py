"""
F.R.I.D.A.Y. V2 — Diagnostics & Health Tools
============================================
Allows FRIDAY to report on its internal subsystems, LiveKit connection status,
active providers, latency, and system resource health.
"""

import json
from friday.core.health import get_health_report
from friday.core.metrics import metrics
from friday.config import config
from friday.core.logging import get_logger

logger = get_logger("diagnostics_tools")


def register(mcp):
    @mcp.tool()
    async def check_system_health() -> str:
        """
        Run a real-time diagnostic audit on FRIDAY's subsystems.
        Reports on LiveKit readiness, database connection, STT/LLM/TTS provider status, and environment.
        """
        try:
            report = get_health_report()
            service_lines = []
            for s in report.services:
                icon = "✅" if s.status == "healthy" else ("⚪" if s.status == "unconfigured" else "⚠️")
                msg = f" ({s.message})" if s.message else ""
                service_lines.append(f"  {icon} **{s.name}**: {s.status.upper()}{msg}")

            lines = [
                f"### F.R.I.D.A.Y. Core Diagnostics (Overall: {report.status.upper()})",
                f"- **Environment**: {config.env.APP_ENV}",
                f"- **Uptime**: {report.uptime_seconds:.1f} seconds",
                f"- **Subsystem Status**:",
                *service_lines,
            ]
            return "\n".join(lines)
        except Exception as exc:
            logger.error("Health check error: %s", exc)
            return f"Diagnostic failure: {exc}"

    @mcp.tool()
    async def get_system_metrics() -> str:
        """
        Retrieve performance metrics: tool call counts, failovers, and latency averages.
        """
        summary = metrics.get_summary()
        lines = [
            "### Performance & Usage Telemetry",
            f"- **Uptime**: {summary.get('uptime_seconds', 0):.1f}s",
            f"- **Counters**: {json.dumps(summary.get('counters', {}), indent=2)}",
        ]
        return "\n".join(lines)
