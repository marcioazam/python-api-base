"""Observability middleware for command bus.

Provides:
- LoggingMiddleware: Structured logging with correlation IDs
- IdempotencyMiddleware: Prevents duplicate command execution
- MetricsMiddleware: Command execution metrics and performance tracking

**Feature: enterprise-features-2025**
**Validates: Requirements 12.1, 12.2, 12.3, 12.4**
"""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from typing import Any, Protocol

logger = logging.getLogger(__name__)

# Context variable for request correlation
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """Get current request ID from context."""
    return request_id_var.get()


def set_request_id(request_id: str) -> None:
    """Set request ID in context."""
    request_id_var.set(request_id)


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())[:8]


# =============================================================================
# Logging Middleware
# =============================================================================


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    """Configuration for logging middleware."""

    log_request: bool = True
    log_response: bool = True
    log_duration: bool = True
    include_command_data: bool = False  # Set True only for debugging
    max_data_length: int = 500


class LoggingMiddleware:
    """Middleware for structured logging with correlation IDs.

    Provides comprehensive logging of command execution including:
    - Request/response logging
    - Duration tracking
    - Correlation ID propagation
    - Structured extra fields for log aggregation

    Example:
        >>> logging_mw = LoggingMiddleware(LoggingConfig(log_duration=True))
        >>> bus.add_middleware(logging_mw)
    """

    def __init__(self, config: LoggingConfig | None = None) -> None:
        """Initialize logging middleware.

        Args:
            config: Logging configuration.
        """
        self._config = config or LoggingConfig()

    def _get_command_data(self, command: Any) -> str | None:
        """Get command data for logging.

        Args:
            command: The command to log.

        Returns:
            String representation of command data or None.
        """
        if not self._config.include_command_data:
            return None

        try:
            if hasattr(command, "model_dump"):
                data = str(command.model_dump())
            elif hasattr(command, "__dict__"):
                data = str(command.__dict__)
            else:
                data = str(command)

            if len(data) > self._config.max_data_length:
                data = data[: self._config.max_data_length] + "..."

            return data
        except Exception:
            return None

    async def __call__(
        self,
        command: Any,
        next_handler: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        """Execute command with logging.

        Args:
            command: The command to execute.
            next_handler: The next handler in the chain.

        Returns:
            Result from the handler.
        """
        command_type = type(command).__name__

        # Get or generate request ID
        request_id = get_request_id()
        if not request_id:
            request_id = generate_request_id()
            set_request_id(request_id)

        extra = {
            "request_id": request_id,
            "command_type": command_type,
            "operation": "COMMAND_EXECUTION",
        }

        # Log request
        if self._config.log_request:
            command_data = self._get_command_data(command)
            if command_data:
                extra["command_data"] = command_data

            logger.info(f"Executing command {command_type}", extra=extra)

        # Execute and measure
        start_time = time.perf_counter()
        error: Exception | None = None

        try:
            result = await next_handler(command)
            return result

        except Exception as e:
            error = e
            raise

        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000

            if self._config.log_duration:
                extra["duration_ms"] = round(duration_ms, 2)

            if self._config.log_response:
                if error:
                    extra["error_type"] = type(error).__name__
                    extra["success"] = False
                    logger.error(
                        f"Command {command_type} failed in {duration_ms:.2f}ms",
                        extra=extra,
                        exc_info=True,
                    )
                else:
                    extra["success"] = True
                    logger.info(
                        f"Command {command_type} completed in {duration_ms:.2f}ms",
                        extra=extra,
                    )


# =============================================================================
# Idempotency Middleware
# =============================================================================


class IdempotencyCache(Protocol):
    """Protocol for idempotency cache implementations."""

    async def get(self, key: str) -> Any | None:
        """Get cached result by key."""
        ...

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """Set cached result with TTL in seconds."""
        ...

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        ...


class InMemoryIdempotencyCache:
    """In-memory idempotency cache for development/testing."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[Any, datetime]] = {}

    async def get(self, key: str) -> Any | None:
        """Get cached result."""
        if key not in self._cache:
            return None

        value, expires_at = self._cache[key]
        if datetime.now(UTC) > expires_at:
            del self._cache[key]
            return None

        return value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """Set cached result."""
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl)
        self._cache[key] = (value, expires_at)

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return await self.get(key) is not None

    def cleanup(self) -> int:
        """Remove expired entries. Returns count of removed entries."""
        now = datetime.now(UTC)
        expired = [k for k, (_, exp) in self._cache.items() if now > exp]
        for k in expired:
            del self._cache[k]
        return len(expired)


@dataclass(frozen=True, slots=True)
class IdempotencyConfig:
    """Configuration for idempotency middleware."""

    ttl_seconds: int = 3600  # 1 hour default
    key_prefix: str = "idempotency"
    header_name: str = "X-Idempotency-Key"


class IdempotencyMiddleware:
    """Middleware that prevents duplicate command execution.

    Uses idempotency keys to detect and prevent duplicate requests.
    Returns cached results for duplicate requests.

    Commands can provide an idempotency key via:
    - `idempotency_key` attribute on the command
    - `get_idempotency_key()` method on the command

    Example:
        >>> cache = InMemoryIdempotencyCache()
        >>> idempotency = IdempotencyMiddleware(cache)
        >>> bus.add_middleware(idempotency)

        >>> @dataclass
        ... class CreateOrderCommand:
        ...     order_id: str
        ...     idempotency_key: str  # Will be used automatically
    """

    def __init__(
        self,
        cache: IdempotencyCache,
        config: IdempotencyConfig | None = None,
    ) -> None:
        """Initialize idempotency middleware.

        Args:
            cache: Cache implementation for storing results.
            config: Idempotency configuration.
        """
        self._cache = cache
        self._config = config or IdempotencyConfig()

    def _get_idempotency_key(self, command: Any) -> str | None:
        """Extract idempotency key from command.

        Args:
            command: The command to extract key from.

        Returns:
            Idempotency key or None if not provided.
        """
        # Try attribute first
        key = getattr(command, "idempotency_key", None)
        if key:
            return str(key)

        # Try method
        get_key = getattr(command, "get_idempotency_key", None)
        if callable(get_key):
            return str(get_key())

        return None

    def _build_cache_key(self, command: Any, idempotency_key: str) -> str:
        """Build full cache key.

        Args:
            command: The command.
            idempotency_key: The idempotency key.

        Returns:
            Full cache key.
        """
        command_type = type(command).__name__
        return f"{self._config.key_prefix}:{command_type}:{idempotency_key}"

    async def __call__(
        self,
        command: Any,
        next_handler: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        """Execute command with idempotency check.

        Args:
            command: The command to execute.
            next_handler: The next handler in the chain.

        Returns:
            Result from handler or cached result.
        """
        command_type = type(command).__name__
        idempotency_key = self._get_idempotency_key(command)

        # No idempotency key - execute normally
        if not idempotency_key:
            return await next_handler(command)

        cache_key = self._build_cache_key(command, idempotency_key)

        # Check for cached result
        cached = await self._cache.get(cache_key)
        if cached is not None:
            logger.info(
                f"Returning cached result for {command_type}",
                extra={
                    "command_type": command_type,
                    "idempotency_key": idempotency_key,
                    "operation": "IDEMPOTENCY_HIT",
                },
            )
            return cached

        # Execute command
        result = await next_handler(command)

        # Cache result
        await self._cache.set(cache_key, result, self._config.ttl_seconds)
        logger.debug(
            f"Cached result for {command_type}",
            extra={
                "command_type": command_type,
                "idempotency_key": idempotency_key,
                "ttl_seconds": self._config.ttl_seconds,
                "operation": "IDEMPOTENCY_CACHE",
            },
        )

        return result


# =============================================================================
# Metrics Middleware
# =============================================================================


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


class InMemoryMetricsCollector:
    """In-memory metrics collector for development/testing."""

    def __init__(self) -> None:
        self._durations: dict[str, list[float]] = {}
        self._counts: dict[str, dict[str, int]] = {}
        self._slow_commands: list[tuple[str, float, datetime]] = []

    def record_command_duration(
        self, command_type: str, duration_ms: float, success: bool
    ) -> None:
        """Record command execution duration."""
        if command_type not in self._durations:
            self._durations[command_type] = []
        self._durations[command_type].append(duration_ms)

    def increment_command_count(self, command_type: str, success: bool) -> None:
        """Increment command execution counter."""
        if command_type not in self._counts:
            self._counts[command_type] = {"success": 0, "failure": 0}

        if success:
            self._counts[command_type]["success"] += 1
        else:
            self._counts[command_type]["failure"] += 1

    def record_slow_command(self, command_type: str, duration_ms: float) -> None:
        """Record slow command execution."""
        self._slow_commands.append((command_type, duration_ms, datetime.now(UTC)))

    def get_statistics(self, command_type: str | None = None) -> dict[str, Any]:
        """Get statistics for command type or all commands."""
        if command_type:
            durations = self._durations.get(command_type, [])
            counts = self._counts.get(command_type, {"success": 0, "failure": 0})

            return {
                "command_type": command_type,
                "total_executions": sum(counts.values()),
                "success_count": counts["success"],
                "failure_count": counts["failure"],
                "success_rate": (
                    counts["success"] / sum(counts.values())
                    if sum(counts.values()) > 0
                    else 0
                ),
                "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
                "min_duration_ms": min(durations) if durations else 0,
                "max_duration_ms": max(durations) if durations else 0,
            }

        return {
            "commands": {
                cmd: self.get_statistics(cmd) for cmd in self._counts.keys()
            },
            "total_commands": sum(
                sum(c.values()) for c in self._counts.values()
            ),
        }


@dataclass(frozen=True, slots=True)
class MetricsConfig:
    """Configuration for metrics middleware."""

    enabled: bool = True
    track_duration: bool = True
    track_success_rate: bool = True
    detect_slow_commands: bool = True
    slow_threshold_ms: float = 1000.0  # Commands slower than 1s are "slow"


class MetricsMiddleware:
    """Middleware for collecting command execution metrics.

    Tracks:
    - Command execution duration
    - Success/failure rates
    - Slow command detection

    Example:
        >>> collector = InMemoryMetricsCollector()
        >>> metrics = MetricsMiddleware(collector, MetricsConfig(slow_threshold_ms=500))
        >>> bus.add_middleware(metrics)

        >>> # Get statistics
        >>> stats = collector.get_statistics("CreateUserCommand")
    """

    def __init__(
        self,
        collector: MetricsCollector,
        config: MetricsConfig | None = None,
    ) -> None:
        """Initialize metrics middleware.

        Args:
            collector: Metrics collector implementation.
            config: Metrics configuration.
        """
        self._collector = collector
        self._config = config or MetricsConfig()

    async def __call__(
        self,
        command: Any,
        next_handler: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        """Execute command with metrics collection.

        Args:
            command: The command to execute.
            next_handler: The next handler in the chain.

        Returns:
            Result from handler.
        """
        if not self._config.enabled:
            return await next_handler(command)

        command_type = type(command).__name__
        start_time = time.perf_counter()
        success = False
        error: Exception | None = None

        try:
            result = await next_handler(command)
            success = True
            return result

        except Exception as e:
            error = e
            raise

        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Track duration
            if self._config.track_duration:
                self._collector.record_command_duration(
                    command_type, duration_ms, success
                )

            # Track success rate
            if self._config.track_success_rate:
                self._collector.increment_command_count(command_type, success)

            # Detect slow commands
            if (
                self._config.detect_slow_commands
                and duration_ms > self._config.slow_threshold_ms
            ):
                self._collector.record_slow_command(command_type, duration_ms)
                logger.warning(
                    f"Slow command detected: {command_type} took {duration_ms:.2f}ms",
                    extra={
                        "command_type": command_type,
                        "duration_ms": duration_ms,
                        "threshold_ms": self._config.slow_threshold_ms,
                        "operation": "SLOW_COMMAND_DETECTED",
                        "success": success,
                    },
                )
