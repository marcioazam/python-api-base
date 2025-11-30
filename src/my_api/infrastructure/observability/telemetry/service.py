"""telemetry service.

**Feature: infrastructure-code-review**
**Validates: Requirements 4.2, 4.3**
"""

import functools
import logging
import threading
from contextvars import ContextVar
from typing import Any, ParamSpec
from collections.abc import Callable
from .noop import _NoOpSpan, _NoOpTracer, _NoOpMeter, _NoOpCounter, _NoOpHistogram

P = ParamSpec("P")

logger = logging.getLogger(__name__)

# Global telemetry instance with thread safety
_telemetry: "TelemetryProvider | None" = None
_telemetry_lock = threading.Lock()

# Context variables for trace/span correlation
_current_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
_current_span_id: ContextVar[str | None] = ContextVar("span_id", default=None)

__all__ = [
    "TelemetryProvider",
    "_NoOpSpan",
    "_NoOpTracer",
    "_NoOpMeter",
    "_NoOpCounter",
    "_NoOpHistogram",
    "get_current_trace_id",
    "get_current_span_id",
    "get_telemetry",
    "init_telemetry",
    "traced",
]


class TelemetryProvider:
    """OpenTelemetry provider for traces, metrics, and logs.

    Initializes and manages OpenTelemetry SDK components with
    OTLP exporters for distributed tracing and metrics collection.

    **Feature: advanced-reusability**
    **Validates: Requirements 4.1, 4.6**
    """

    def __init__(
        self,
        service_name: str = "my-api",
        service_version: str = "0.1.0",
        otlp_endpoint: str | None = None,
        enable_tracing: bool = True,
        enable_metrics: bool = True,
    ) -> None:
        """Initialize telemetry provider.

        Args:
            service_name: Name of the service for resource attributes.
            service_version: Version of the service.
            otlp_endpoint: OTLP collector endpoint. None disables export.
            enable_tracing: Whether to enable distributed tracing.
            enable_metrics: Whether to enable metrics collection.
        """
        self._service_name = service_name
        self._service_version = service_version
        self._otlp_endpoint = otlp_endpoint
        self._enable_tracing = enable_tracing
        self._enable_metrics = enable_metrics

        self._tracer_provider: Any = None
        self._meter_provider: Any = None
        self._tracer: Any = None
        self._meter: Any = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize OpenTelemetry SDK components.

        Sets up TracerProvider and MeterProvider with OTLP exporters
        if an endpoint is configured.
        """
        if self._initialized:
            return

        try:
            self._setup_tracing()
            self._setup_metrics()
            self._initialized = True
            logger.info(
                f"Telemetry initialized for {self._service_name} "
                f"(tracing={self._enable_tracing}, metrics={self._enable_metrics})"
            )
        except ImportError as e:
            logger.warning(f"OpenTelemetry packages not installed: {e}")
        except Exception as e:
            logger.warning(f"Failed to initialize telemetry: {e}")

    def _setup_tracing(self) -> None:
        """Set up distributed tracing with OTLP exporter."""
        if not self._enable_tracing:
            return

        try:
            from opentelemetry import trace
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            # Create resource with service info
            resource = Resource.create({
                "service.name": self._service_name,
                "service.version": self._service_version,
            })

            # Create tracer provider
            self._tracer_provider = TracerProvider(resource=resource)

            # Add OTLP exporter if endpoint configured
            if self._otlp_endpoint:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                    OTLPSpanExporter,
                )

                otlp_exporter = OTLPSpanExporter(endpoint=self._otlp_endpoint)
                self._tracer_provider.add_span_processor(
                    BatchSpanProcessor(otlp_exporter)
                )

            # Set as global tracer provider
            trace.set_tracer_provider(self._tracer_provider)
            self._tracer = trace.get_tracer(self._service_name)

        except ImportError:
            logger.debug("OpenTelemetry tracing packages not available")

    def _setup_metrics(self) -> None:
        """Set up metrics collection with OTLP exporter."""
        if not self._enable_metrics:
            return

        try:
            from opentelemetry import metrics
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.resources import Resource

            resource = Resource.create({
                "service.name": self._service_name,
                "service.version": self._service_version,
            })

            self._meter_provider = MeterProvider(resource=resource)

            # Add OTLP exporter if endpoint configured
            if self._otlp_endpoint:
                from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                    OTLPMetricExporter,
                )
                from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

                otlp_exporter = OTLPMetricExporter(endpoint=self._otlp_endpoint)
                reader = PeriodicExportingMetricReader(otlp_exporter)
                self._meter_provider = MeterProvider(
                    resource=resource,
                    metric_readers=[reader],
                )

            metrics.set_meter_provider(self._meter_provider)
            self._meter = metrics.get_meter(self._service_name)

        except ImportError:
            logger.debug("OpenTelemetry metrics packages not available")

    def get_tracer(self) -> Any:
        """Get the configured tracer.

        Returns:
            OpenTelemetry Tracer or NoOpTracer if not initialized.
        """
        if self._tracer is None:
            return _NoOpTracer()
        return self._tracer

    def get_meter(self) -> Any:
        """Get the configured meter.

        Returns:
            OpenTelemetry Meter or NoOpMeter if not initialized.
        """
        if self._meter is None:
            return _NoOpMeter()
        return self._meter

    async def shutdown(self) -> None:
        """Gracefully shutdown telemetry providers."""
        if self._tracer_provider is not None:
            try:
                self._tracer_provider.shutdown()
            except Exception as e:
                logger.warning(f"Error shutting down tracer: {e}")

        if self._meter_provider is not None:
            try:
                self._meter_provider.shutdown()
            except Exception as e:
                logger.warning(f"Error shutting down meter: {e}")

        self._initialized = False


def get_current_trace_id() -> str | None:
    """Get the current trace ID from context."""
    return _current_trace_id.get()

def get_current_span_id() -> str | None:
    """Get the current span ID from context."""
    return _current_span_id.get()

def get_telemetry() -> TelemetryProvider:
    """Get or create the global telemetry provider.

    Returns:
        TelemetryProvider instance.
    """
    global _telemetry
    with _telemetry_lock:
        if _telemetry is None:
            _telemetry = TelemetryProvider()
        return _telemetry

def init_telemetry(
    service_name: str = "my-api",
    service_version: str = "0.1.0",
    otlp_endpoint: str | None = None,
    enable_tracing: bool = True,
    enable_metrics: bool = True,
) -> TelemetryProvider:
    """Initialize the global telemetry provider.

    Args:
        service_name: Name of the service.
        service_version: Version of the service.
        otlp_endpoint: OTLP collector endpoint.
        enable_tracing: Whether to enable tracing.
        enable_metrics: Whether to enable metrics.

    Returns:
        Initialized TelemetryProvider.
    """
    global _telemetry
    with _telemetry_lock:
        _telemetry = TelemetryProvider(
            service_name=service_name,
            service_version=service_version,
            otlp_endpoint=otlp_endpoint,
            enable_tracing=enable_tracing,
            enable_metrics=enable_metrics,
        )
        _telemetry.initialize()
        return _telemetry

def traced[T](
    name: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator for creating custom spans around functions.

    Creates a span for the decorated function, recording exceptions
    and setting attributes. Supports both sync and async functions.

    **Feature: advanced-reusability**
    **Validates: Requirements 4.5**

    Args:
        name: Span name. Defaults to function qualified name.
        attributes: Additional span attributes.

    Returns:
        Decorated function with tracing.

    Example:
        >>> @traced(name="fetch_user", attributes={"db": "postgres"})
        ... async def get_user(user_id: str) -> User:
        ...     return await db.fetch_user(user_id)
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        span_name = name or f"{func.__module__}.{func.__qualname__}"

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            tracer = get_telemetry().get_tracer()

            with tracer.start_as_current_span(span_name) as span:
                # Set attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                # Update context vars for log correlation
                try:
                    from opentelemetry import trace

                    ctx = trace.get_current_span().get_span_context()
                    if ctx.is_valid:
                        _current_trace_id.set(format(ctx.trace_id, "032x"))
                        _current_span_id.set(format(ctx.span_id, "016x"))
                except Exception:
                    pass

                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    try:
                        from opentelemetry.trace import StatusCode

                        span.set_status(StatusCode.ERROR, str(e))
                    except ImportError:
                        pass
                    raise

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            tracer = get_telemetry().get_tracer()

            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                try:
                    from opentelemetry import trace

                    ctx = trace.get_current_span().get_span_context()
                    if ctx.is_valid:
                        _current_trace_id.set(format(ctx.trace_id, "032x"))
                        _current_span_id.set(format(ctx.span_id, "016x"))
                except Exception:
                    pass

                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    try:
                        from opentelemetry.trace import StatusCode

                        span.set_status(StatusCode.ERROR, str(e))
                    except ImportError:
                        pass
                    raise

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator
