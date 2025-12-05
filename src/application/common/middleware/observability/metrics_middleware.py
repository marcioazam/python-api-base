"""Metrics middleware for command bus.

Command execution metrics and performance tracking.

**Feature: enterprise-features-2025**
**Validates: Requirements 12.4**
**Refactored: Improved type safety, lazy logging, defaultdict usage**
"""

import logging
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class MetricsCollector(Protocol):
    """Protocol for metrics collection implementations."""

    def record_command_duration(
        self, command_type: str, duration_ms: float, success: bool
    ) -> None:
        """Record command execution duration."""
        ...

    def increment_command_count(self, command_type: str, success: bool) -> None:
        """Increment command execution counter."""
        ...

    def record_slow_command(self, command_type: str, duration_ms: float) -> None:
        """Record slow command execution."""
        ...


@dataclass
class InMemoryMetricsCollector:
    """In-memory metrics collector for development/testing."""

    _durations: dict[str, list[float]] = field(
        default_factory=lambda: defaultdict(list)
    )
    _counts: dict[str, dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: {"success": 0, "failure": 0})
    )
    _slow_commands: list[tuple[str, float, datetime]] = field(default_factory=list)

    def record_command_duration(
        self,
        command_type: str,
        duration_ms: float,
        success: bool,  # noqa: ARG002 - protocol compliance
    ) -> None:
        """Record command execution duration."""
        self._durations[command_type].append(duration_ms)

    def increment_command_count(self, command_type: str, success: bool) -> None:
        """Increment command execution counter."""
        key = "success" if success else "failure"
        self._counts[command_type][key] += 1

    def record_slow_command(self, command_type: str, duration_ms: float) -> None:
        """Record slow command execution."""
        self._slow_commands.append((command_type, duration_ms, datetime.now(UTC)))

    def get_statistics(self, command_type: str | None = None) -> dict[str, Any]:
        """Get statistics for command type or all commands."""
        if command_type:
            return self._get_single_statistics(command_type)

        return {
            "commands": {cmd: self._get_single_statistics(cmd) for cmd in self._counts},
            "total_commands": sum(sum(c.values()) for c in self._counts.values()),
        }

    def _get_single_statistics(self, command_type: str) -> dict[str, Any]:
        """Get statistics for a single command type."""
        durations = self._durations.get(command_type, [])
        counts = self._counts.get(command_type, {"success": 0, "failure": 0})
        total = sum(counts.values())

        return {
            "command_type": command_type,
            "total_executions": total,
            "success_count": counts["success"],
            "failure_count": counts["failure"],
            "success_rate": counts["success"] / total if total > 0 else 0,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "min_duration_ms": min(durations) if durations else 0,
            "max_duration_ms": max(durations) if durations else 0,
        }


@dataclass(frozen=True, slots=True)
class MetricsConfig:
    """Configuration for metrics middleware."""

    enabled: bool = True
    track_duration: bool = True
    track_success_rate: bool = True
    detect_slow_commands: bool = True
    slow_threshold_ms: float = 1000.0


class MetricsMiddleware:
    """Middleware for collecting command execution metrics.

    Tracks:
    - Command execution duration
    - Success/failure rates
    - Slow command detection
    """

    def __init__(
        self,
        collector: MetricsCollector,
        config: MetricsConfig | None = None,
    ) -> None:
        """Initialize metrics middleware."""
        self._collector = collector
        self._config = config or MetricsConfig()

    async def __call__(
        self,
        command: Any,
        next_handler: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        """Execute command with metrics collection."""
        if not self._config.enabled:
            return await next_handler(command)

        command_type = type(command).__name__
        start_time = time.perf_counter()
        success = False

        try:
            result = await next_handler(command)
            success = True
            return result
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000

            if self._config.track_duration:
                self._collector.record_command_duration(
                    command_type, duration_ms, success
                )

            if self._config.track_success_rate:
                self._collector.increment_command_count(command_type, success)

            if (
                self._config.detect_slow_commands
                and duration_ms > self._config.slow_threshold_ms
            ):
                self._collector.record_slow_command(command_type, duration_ms)
                logger.warning(
                    "Slow command detected: %s took %.2fms",
                    command_type,
                    duration_ms,
                    extra={
                        "command_type": command_type,
                        "duration_ms": duration_ms,
                        "threshold_ms": self._config.slow_threshold_ms,
                        "operation": "SLOW_COMMAND_DETECTED",
                        "success": success,
                    },
                )
