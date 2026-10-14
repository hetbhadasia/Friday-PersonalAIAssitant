"""
F.R.I.D.A.Y. V2 — Master Orchestration & Entry Point
===================================================
Run all or individual FRIDAY services:
  python main.py              # Starts Token Server and MCP Server concurrently
  python main.py --all        # Starts Token Server, MCP Server, and opens instructions
  python main.py --mcp        # FastMCP Server on :8000
  python main.py --token      # Token & Health Server on :8080
  python main.py --agent      # LiveKit Voice Agent
  python main.py --audit      # Run system configuration & health diagnostic
"""

import sys
import os
import argparse
import asyncio
import subprocess
import signal

from friday.config import config
from friday.core.logging import get_logger, setup_logging
from friday.core.health import health_checker

logger = get_logger("orchestrator")


def run_audit():
    """Perform pre-flight configuration audit."""
    print("=" * 60)
    print("🤖 F.R.I.D.A.Y. V2 — System Diagnostic Audit")
    print("=" * 60)
    warnings = config.validate()
    if warnings:
        print("\n⚠️ Configuration Warnings:")
        for w in warnings:
            print(f"  • {w}")
    else:
        print("\n✅ Configuration: All primary credentials detected.")

    report = health_checker.check_all()
    print(f"\nSubsystems Status ({report.status.upper()}):")
    for s in report.services:
        status_sym = "✅" if s.status == "healthy" else ("⚪" if s.status == "unconfigured" else "❌")
        print(f"  {status_sym} {s.name.ljust(18)} : {s.status} ({s.message})")

    print("\nNetwork Bindings:")
    print(f"  • MCP Server Host  : {config.server.mcp_server_url}")
    print(f"  • Token Server Host: http://{config.server.TOKEN_SERVER_HOST}:{config.server.TOKEN_SERVER_PORT}")
    print("=" * 60)


def start_mcp_server():
    """Run FastMCP server."""
    from server import main as mcp_main
    print(f"🚀 Starting FastMCP Server on port {config.server.MCP_SERVER_PORT}...")
    mcp_main()


def start_token_server():
    """Run Token & Health server."""
    from aiohttp import web
    from token_server import create_app
    host = config.server.TOKEN_SERVER_HOST
    port = config.server.TOKEN_SERVER_PORT
    print(f"🛡️ Starting Token & Health Server on http://{host}:{port}...")
    web.run_app(create_app(), host=host, port=port, print=None)


def start_agent():
    """Run LiveKit voice agent."""
    from agent_friday import dev as agent_dev
    print("🎙️ Starting FRIDAY Voice Agent...")
    agent_dev()


async def run_concurrent():
    """Run Token Server and MCP Server concurrently."""
    run_audit()

    print("\n" + "=" * 60)
    print("🌟 F.R.I.D.A.Y. V2 Ecosystem Launching...")
    print("=" * 60)
    print("1. MCP Server running at :8000/sse")
    print("2. Token Server running at :8080 (endpoints: /api/token, /health, /metrics)")
    print("3. Frontend can be launched via: cd frontend && npm run dev")
    print("4. LiveKit Voice Agent can be launched via: uv run agent_friday.py dev")
    print("=" * 60 + "\n")

    python_bin = sys.executable

    # Start MCP server subprocess
    mcp_proc = subprocess.Popen([python_bin, "server.py"])

    # Start Token server subprocess
    token_proc = subprocess.Popen([python_bin, "token_server.py"])

    procs = [mcp_proc, token_proc]

    def shutdown(sig, frame):
        print("\nInitiating graceful shutdown of FRIDAY services...")
        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            await asyncio.sleep(1)
            # Check if any exited unexpectedly
            for p in procs:
                if p.poll() is not None:
                    print(f"Process {p.pid} terminated unexpectedly with code {p.returncode}")
                    shutdown(None, None)
    except (KeyboardInterrupt, asyncio.CancelledError):
        shutdown(None, None)


def main():
    parser = argparse.ArgumentParser(description="F.R.I.D.A.Y. V2 Orchestrator")
    parser.add_argument("--mcp", action="store_true", help="Start FastMCP server only")
    parser.add_argument("--token", action="store_true", help="Start Token & Health server only")
    parser.add_argument("--agent", action="store_true", help="Start LiveKit Voice Agent only")
    parser.add_argument("--audit", action="store_true", help="Run diagnostic health and config audit")
    parser.add_argument("--all", action="store_true", help="Start all servers concurrently")

    args = parser.parse_args()

    if args.audit:
        run_audit()
    elif args.mcp:
        start_mcp_server()
    elif args.token:
        start_token_server()
    elif args.agent:
        start_agent()
    else:
        # Default behavior: run concurrent servers
        asyncio.run(run_concurrent())


if __name__ == "__main__":
    main()
