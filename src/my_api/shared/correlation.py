"""Correlation ID for request tracing across services.

This module provides correlation ID generation and propagation
for distributed tracing and log correlation.

**Feature: api-architecture-analysis**
**Validates: Requirements 7.5**
"""

import contextvars
import uuid
from dataclasses import dataclass
from datetime import datetime, UTC
from enum import Enum
from typing import Any
from collections.abc import Callable


# Context variable for correlation ID
_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)
_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
_span_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "span_id", default=None
)
_parent_span_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "parent_span_id", default=None
)


class IdFormat(Enum):
    """Format for generated IDs."""

    UUID4 = "uuid4"
    UUID4_HEX = "uuid4_hex"
    SHORT = "short"  # 16 chars
    TIMESTAMP = "timestamp"  # Includes timestamp prefix


def generate_id(format: IdFormat = IdFormat.UUID4_HEX) -> str:
    """Generate a unique ID in the specified format."""
    if format == IdFormat.UUID4:
        return str(uuid.uuid4())
    elif format == IdFormat.UUID4_HEX:
        return uuid.uuid4().hex
    elif format == IdFormat.SHORT:
        return uuid.uuid4().hex[:16]
    elif format == IdFormat.TIMESTAMP:
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        return f"{timestamp}-{uuid.uuid4().hex[:12]}"
    return uuid.uuid4().hex


def get_correlation_id() -> str | None:
    """Get the current correlation ID from context."""
    return _correlation_id.get()


def set_correlation_id(correlation_id: str) -> contextvars.Token[str | None]:
    """Set the correlation ID in context."""
    return _correlation_id.set(correlation_id)


def get_request_id() -> str | None:
    """Get the current request ID from context."""
    return _request_id.get()


def set_request_id(request_id: str) -> contextvars.Token[str | None]:
    """Set the request ID in context."""
    return _request_id.set(request_id)


def get_span_id() -> str | None:
    """Get the current span ID from context."""
    return _span_id.get()


def set_span_id(span_id: str) -> contextvars.Token[str | None]:
    """Set the span ID in context."""
    return _span_id.set(span_id)


def get_parent_span_id() -> str | None:
    """Get the parent span ID from context."""
    return _parent_span_id.get()


def set_parent_span_id(parent_span_id: str) -> contextvars.Token[str | None]:
    """Set the parent span ID in context."""
    return _parent_span_id.set(parent_span_id)


def clear_context() -> None:
    """Clear all correlation context."""
    _correlation_id.set(None)
    _request_id.set(None)
    _span_id.set(None)
    _parent_span_id.set(None)


@dataclass
class CorrelationContext:
    """Complete correlation context for a request."""

    correlation_id: str
    request_id: str
    span_id: str | None = None
    parent_span_id: str | None = None
    trace_id: str | None = None
    service_name: str | None = None
    timestamp: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/headers."""
        result: dict[str, Any] = {
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
        }
        if self.span_id:
            result["span_id"] = self.span_id
        if self.parent_span_id:
            result["parent_span_id"] = self.parent_span_id
        if self.trace_id:
            result["trace_id"] = self.trace_id
        if self.service_name:
            result["service_name"] = self.service_name
        if self.timestamp:
            result["timestamp"] = self.timestamp.isoformat()
        return result

    def to_headers(self) -> dict[str, str]:
        """Convert to HTTP headers."""
        headers = {
            "X-Correlation-ID": self.correlation_id,
            "X-Request-ID": self.request_id,
        }
        if self.span_id:
            headers["X-Span-ID"] = self.span_id
        if self.parent_span_id:
            headers["X-Parent-Span-ID"] = self.parent_span_id
        if self.trace_id:
            headers["X-Trace-ID"] = self.trace_id
        return headers

    @classmethod
    def from_headers(
        cls,
        headers: dict[str, str],
        generate_missing: bool = True,
        id_format: IdFormat = IdFormat.UUID4_HEX,
    ) -> "CorrelationContext":
        """Create context from HTTP headers."""
        correlation_id = headers.get("X-Correlation-ID", "")
        request_id = headers.get("X-Request-ID", "")

        if generate_missing:
            if not correlation_id:
                correlation_id = generate_id(id_format)
            if not request_id:
                request_id = generate_id(id_format)

        return cls(
            correlation_id=correlation_id,
            request_id=request_id,
            span_id=headers.get("X-Span-ID"),
            parent_span_id=headers.get("X-Parent-Span-ID"),
            trace_id=headers.get("X-Trace-ID"),
            timestamp=datetime.now(UTC),
        )

    @classmethod
    def create_new(
        cls,
        service_name: str | None = None,
        id_format: IdFormat = IdFormat.UUID4_HEX,
    ) -> "CorrelationContext":
        """Create a new correlation context."""
        return cls(
            correlation_id=generate_id(id_format),
            request_id=generate_id(id_format),
            span_id=generate_id(IdFormat.SHORT),
            service_name=service_name,
            timestamp=datetime.now(UTC),
        )


class CorrelationContextManager:
    """Context manager for correlation context with safe token handling.

    **Feature: shared-modules-security-fixes**
    **Validates: Requirements 6.1, 6.2, 6.3**
    """

    def __init__(
        self,
        context: CorrelationContext | None = None,
        service_name: str | None = None,
    ) -> None:
        self._context = context or CorrelationContext.create_new(service_name)
        self._tokens: list[contextvars.Token[str | None]] = []
        self._entered = False

    def __enter__(self) -> CorrelationContext:
        """Enter context and set correlation IDs."""
        if self._entered:
            # Already entered - log warning and return existing context
            import logging
            logging.getLogger(__name__).warning(
                "CorrelationContextManager entered multiple times"
            )
            return self._context

        self._entered = True
        self._tokens.append(set_correlation_id(self._context.correlation_id))
        self._tokens.append(set_request_id(self._context.request_id))
        if self._context.span_id:
            self._tokens.append(set_span_id(self._context.span_id))
        if self._context.parent_span_id:
            self._tokens.append(set_parent_span_id(self._context.parent_span_id))
        return self._context

    def __exit__(self, *args: Any) -> None:
        """Exit context and safely restore previous values.

        Handles already-reset tokens gracefully by catching ValueError
        and logging a warning instead of raising an exception.
        """
        import logging
        logger = logging.getLogger(__name__)

        for token in reversed(self._tokens):
            try:
                if hasattr(token, "var"):
                    token.var.reset(token)
            except ValueError:
                # Token already reset - log and continue
                logger.warning(
                    "Correlation context token already reset",
                    extra={"token_var": getattr(token, "var", None)},
                )

        self._tokens.clear()
        self._entered = False


def get_current_context() -> CorrelationContext | None:
    """Get the current correlation context from context vars."""
    correlation_id = get_correlation_id()
    request_id = get_request_id()

    if not correlation_id or not request_id:
        return None

    return CorrelationContext(
        correlation_id=correlation_id,
        request_id=request_id,
        span_id=get_span_id(),
        parent_span_id=get_parent_span_id(),
    )


def with_correlation(
    correlation_id: str | None = None,
    request_id: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to run function with correlation context."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            context = CorrelationContext(
                correlation_id=correlation_id or generate_id(),
                request_id=request_id or generate_id(),
            )
            with CorrelationContextManager(context):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def propagate_correlation(
    func: Callable[..., Any],
) -> Callable[..., Any]:
    """Decorator to propagate existing correlation context."""
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Get current context or create new
        context = get_current_context()
        if context:
            # Create child span
            new_context = CorrelationContext(
                correlation_id=context.correlation_id,
                request_id=context.request_id,
                span_id=generate_id(IdFormat.SHORT),
                parent_span_id=context.span_id,
            )
            with CorrelationContextManager(new_context):
                return func(*args, **kwargs)
        return func(*args, **kwargs)
    return wrapper


# Structlog processor for correlation
def add_correlation_context(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Structlog processor to add correlation context to logs."""
    correlation_id = get_correlation_id()
    request_id = get_request_id()
    span_id = get_span_id()

    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    if request_id:
        event_dict["request_id"] = request_id
    if span_id:
        event_dict["span_id"] = span_id

    return event_dict


@dataclass
class CorrelationConfig:
    """Configuration for correlation ID handling."""

    header_name: str = "X-Correlation-ID"
    request_id_header: str = "X-Request-ID"
    generate_if_missing: bool = True
    id_format: IdFormat = IdFormat.UUID4_HEX
    propagate_to_response: bool = True
    service_name: str | None = None


class CorrelationService:
    """Service for managing correlation context."""

    def __init__(self, config: CorrelationConfig | None = None) -> None:
        self._config = config or CorrelationConfig()

    def extract_from_headers(self, headers: dict[str, str]) -> CorrelationContext:
        """Extract correlation context from request headers."""
        return CorrelationContext.from_headers(
            headers,
            generate_missing=self._config.generate_if_missing,
            id_format=self._config.id_format,
        )

    def create_context(self) -> CorrelationContext:
        """Create a new correlation context."""
        return CorrelationContext.create_new(
            service_name=self._config.service_name,
            id_format=self._config.id_format,
        )

    def get_response_headers(self, context: CorrelationContext) -> dict[str, str]:
        """Get headers to add to response."""
        if not self._config.propagate_to_response:
            return {}
        return context.to_headers()

    def bind_context(self, context: CorrelationContext) -> CorrelationContextManager:
        """Create a context manager for the given context."""
        return CorrelationContextManager(context, self._config.service_name)


# Convenience factory
def create_correlation_service(
    config: CorrelationConfig | None = None,
) -> CorrelationService:
    """Create a CorrelationService with defaults."""
    return CorrelationService(config=config)
