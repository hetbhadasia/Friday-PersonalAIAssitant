"""
F.R.I.D.A.Y. V2 — Metrics Collector
====================================
Lightweight internal metrics for observability.
No external infrastructure required.
"""

import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LatencyStats:
    count: int = 0
    total_ms: float = 0
    min_ms: float = float("inf")
    max_ms: float = 0

    def record(self, ms: float):
        self.count += 1
        self.total_ms += ms
        self.min_ms = min(self.min_ms, ms)
        self.max_ms = max(self.max_ms, ms)

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.count if self.count else 0

    def to_dict(self) -> dict:
        if self.count == 0:
            return {"count": 0}
        return {
            "count": self.count,
            "avg_ms": round(self.avg_ms, 1),
            "min_ms": round(self.min_ms, 1),
            "max_ms": round(self.max_ms, 1),
        }


class MetricsCollector:
    """
    Thread-safe in-process metrics collector.
    
    Tracks:
    - Request counts by category
    - Error counts by category
    - Latency statistics by operation
    - Active session count
    - Provider failover events
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._counters: dict[str, int] = defaultdict(int)
        self._latencies: dict[str, LatencyStats] = defaultdict(LatencyStats)
        self._active_sessions: int = 0
        self._start_time = time.monotonic()

    def increment(self, counter: str, amount: int = 1):
        """Increment a named counter."""
        with self._lock:
            self._counters[counter] += amount

    def record_latency(self, operation: str, ms: float):
        """Record latency for an operation."""
        with self._lock:
            self._latencies[operation].record(ms)

    def session_started(self):
        with self._lock:
            self._active_sessions += 1
            self._counters["sessions_total"] += 1

    def session_ended(self):
        with self._lock:
            self._active_sessions = max(0, self._active_sessions - 1)

    def record_error(self, category: str):
        self.increment(f"errors_{category}")

    def record_tool_call(self, tool_name: str):
        self.increment(f"tool_{tool_name}")
        self.increment("tool_calls_total")

    def record_provider_failover(self, provider_type: str, from_provider: str, to_provider: str):
        self.increment(f"failover_{provider_type}")
        self.increment("failovers_total")

    def get_snapshot(self) -> dict:
        """Return a snapshot of all current metrics."""
        with self._lock:
            return {
                "uptime_seconds": round(time.monotonic() - self._start_time, 1),
                "active_sessions": self._active_sessions,
                "counters": dict(self._counters),
                "latencies": {
                    name: stats.to_dict()
                    for name, stats in self._latencies.items()
                },
            }

    get_summary = get_snapshot

    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._latencies.clear()
            self._active_sessions = 0


# Singleton
metrics = MetricsCollector()
