"""Logging middleware for command bus.

Provides structured logging with correlation IDs.

**Feature: enterprise-features-2025**
**Validates: Requirements 12.1, 12.2**
"""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

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


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    """Configuration for logging middleware."""

    log_request: bool = True
    log_response: bool = True
    log_duration: bool = True
    include_command_data: bool = False
    max_data_length: int = 500


class LoggingMiddleware:
    """Middleware for structured logging with correlation IDs.

    Provides comprehensive logging of command execution including:
    - Request/response logging
    - Duration tracking
    - Correlation ID propagation
    - Structured extra fields for log aggregation
    """

    def __init__(self, config: LoggingConfig | None = None) -> None:
        """Initialize logging middleware."""
        self._config = config or LoggingConfig()

    def _get_command_data(self, command: Any) -> str | None:
        """Get command data for logging."""
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
        """Execute command with logging."""
        command_type = type(command).__name__

        request_id = get_request_id()
        if not request_id:
            request_id = generate_request_id()
            set_request_id(request_id)

        extra = {
            "request_id": request_id,
            "command_type": command_type,
            "operation": "COMMAND_EXECUTION",
        }

        if self._config.log_request:
            command_data = self._get_command_data(command)
            if command_data:
                extra["command_data"] = command_data
            logger.info(f"Executing command {command_type}", extra=extra)

        start_time = time.perf_counter()
        error: Exception | None = None

        try:
            return await next_handler(command)
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
