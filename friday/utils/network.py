"""
F.R.I.D.A.Y. V2 — Network Utilities
====================================
MCP URL resolution, URL validation, and HTTP helpers.
"""

import os
import subprocess
import re
from urllib.parse import urlparse

from friday.config import config
from friday.core.logging import get_logger

logger = get_logger("network")


def resolve_mcp_url(port: int | None = None) -> str:
    """
    Resolve the MCP server URL based on configuration.
    
    Priority:
    1. MCP_SERVER_URL env var (full URL override)
    2. Config-based construction from host + port + transport
    3. WSL auto-detection fallback
    """
    # Full URL override
    full_url = os.getenv("MCP_SERVER_URL")
    if full_url:
        logger.info("MCP URL from MCP_SERVER_URL: %s", full_url)
        return full_url

    # Config-based
    host = config.server.MCP_SERVER_HOST
    port = port or config.server.MCP_SERVER_PORT
    transport = config.server.MCP_TRANSPORT

    # WSL auto-detection if host is "auto"
    if host.lower() == "auto":
        host = _detect_host_ip()

    url = f"http://{host}:{port}/{transport}"
    logger.info("MCP URL resolved: %s", url)
    return url


def _detect_host_ip() -> str:
    """Auto-detect the host IP. Handles normal, WSL, and Docker environments."""
    # Check if running in WSL
    if _is_wsl():
        ip = _get_wsl_host_ip()
        if ip:
            return ip

    # Check if running in Docker
    if _is_docker():
        return "host.docker.internal"

    return "127.0.0.1"


def _is_wsl() -> bool:
    """Check if running inside WSL."""
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower() or "wsl" in f.read().lower()
    except (FileNotFoundError, PermissionError):
        return False


def _is_docker() -> bool:
    """Check if running inside a Docker container."""
    try:
        with open("/proc/1/cgroup", "r") as f:
            return "docker" in f.read()
    except (FileNotFoundError, PermissionError):
        return False


def _get_wsl_host_ip() -> str | None:
    """Resolve Windows host IP from inside WSL."""
    # Try default gateway
    try:
        result = subprocess.run(
            "ip route show default | awk '{print $3}'",
            shell=True, capture_output=True, text=True, timeout=2,
        )
        ip = result.stdout.strip()
        if ip and _is_valid_ip(ip):
            logger.info("WSL host IP via gateway: %s", ip)
            return ip
    except Exception as exc:
        logger.warning("WSL gateway detection failed: %s", exc)

    # Fallback: resolv.conf
    try:
        with open("/etc/resolv.conf", "r") as f:
            for line in f:
                if "nameserver" in line:
                    ip = line.split()[1]
                    if _is_valid_ip(ip):
                        logger.info("WSL host IP via resolv.conf: %s", ip)
                        return ip
    except Exception:
        pass

    return None


def _is_valid_ip(ip: str) -> bool:
    """Basic IPv4 validation."""
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    return all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)


def validate_url(url: str, allowed_schemes: list[str] | None = None) -> tuple[bool, str]:
    """
    Validate a URL for safety.
    
    Returns (is_valid, error_message).
    """
    if not url or not isinstance(url, str):
        return False, "URL is empty or not a string"

    url = url.strip()
    if len(url) > 2048:
        return False, "URL exceeds maximum length (2048 characters)"

    try:
        parsed = urlparse(url)
    except Exception:
        return False, "URL could not be parsed"

    if not parsed.scheme:
        return False, "URL has no scheme (missing http:// or https://)"

    schemes = allowed_schemes or config.content.FETCH_URL_ALLOWED_SCHEMES
    if parsed.scheme.lower() not in schemes:
        return False, f"URL scheme '{parsed.scheme}' is not allowed. Allowed: {schemes}"

    if not parsed.netloc:
        return False, "URL has no host"

    # Block private/internal IPs
    hostname = parsed.hostname or ""
    blocked = ["localhost", "127.0.0.1", "0.0.0.0", "169.254.", "10.", "192.168.", "172.16."]
    if any(hostname.startswith(b) or hostname == b for b in blocked):
        return False, f"URL points to a private/internal address: {hostname}"

    return True, ""


def sanitize_search_query(query: str) -> str:
    """Sanitize a search query — strip dangerous characters, limit length."""
    if not query:
        return ""
    # Remove control characters and excessive whitespace
    query = re.sub(r'[\x00-\x1f\x7f]', '', query)
    query = re.sub(r'\s+', ' ', query).strip()
    # Limit length
    return query[:500]
