"""Tracing middleware for HTTP request instrumentation.

This module provides middleware for automatic HTTP request tracing
with OpenTelemetry, including context propagation and metrics.

**Feature: advanced-reusability**
**Validates: Requirements 4.2, 4.3**
"""

import time
from typing import Any
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from infrastructure.observability.telemetry import (
    _current_span_id,
    _current_trace_id,
    get_telemetry,
)


class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware for HTTP request tracing with OpenTelemetry.

    Creates spans for each HTTP request with:
    - Request method, path, and query parameters
    - Response status code
    - Request duration
    - Trace context propagation from/to headers

    **Feature: advanced-reusability**
    **Validates: Requirements 4.2, 4.3**
    """

    def __init__(
        self,
        app: Any,
        service_name: str = "my-api",
        excluded_paths: list[str] | None = None,
    ) -> None:
        """Initialize tracing middleware.

        Args:
            app: ASGI application.
            service_name: Service name for span attributes.
            excluded_paths: Paths to exclude from tracing (e.g., health checks).
        """
        super().__init__(app)
        self._service_name = service_name
        self._excluded_paths = excluded_paths or ["/health/live", "/health/ready"]
        self._request_counter: Any = None
        self._request_duration: Any = None
        self._setup_metrics()

    def _setup_metrics(self) -> None:
        """Set up request metrics."""
        meter = get_telemetry().get_meter()
        self._request_counter = meter.create_counter(
            name="http_requests_total",
            description="Total HTTP requests",
            unit="1",
        )
        self._request_duration = meter.create_histogram(
            name="http_request_duration_seconds",
            description="HTTP request duration in seconds",
            unit="s",
        )

    def _should_trace(self, path: str) -> bool:
        """Check if the path should be traced.

        Args:
            path: Request path.

        Returns:
            True if path should be traced.
        """
        return path not in self._excluded_paths

    def _extract_trace_context(self, request: Request) -> dict[str, str] | None:
        """Extract trace context from request headers.

        Args:
            request: HTTP request.

        Returns:
            Trace context dict or None.
        """
        try:
            from opentelemetry.propagate import extract

            return extract(dict(request.headers))
        except ImportError:
            return None

    def _inject_trace_context(self, headers: dict[str, str]) -> None:
        """Inject trace context into response headers."""
        try:
            from opentelemetry.propagate import inject

            inject(headers)
        except ImportError:
            pass

    def _set_request_attributes(self, span: Any, request: Request) -> None:
        """Set HTTP request attributes on span."""
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", str(request.url))
        span.set_attribute("http.route", request.url.path)
        span.set_attribute("http.scheme", request.url.scheme)
        span.set_attribute("http.host", request.url.hostname or "")

        user_agent = request.headers.get("user-agent")
        if user_agent:
            span.set_attribute("http.user_agent", user_agent)

    def _update_trace_context_vars(self) -> None:
        """Update context vars for log correlation."""
        try:
            from opentelemetry import trace

            ctx = trace.get_current_span().get_span_context()
            if ctx.is_valid:
                _current_trace_id.set(format(ctx.trace_id, "032x"))
                _current_span_id.set(format(ctx.span_id, "016x"))
        except Exception:
            pass

    def _set_response_status(self, span: Any, status_code: int) -> None:
        """Set span status based on HTTP status code."""
        span.set_attribute("http.status_code", status_code)
        if status_code >= 400:
            try:
                from opentelemetry.trace import StatusCode

                span.set_status(
                    StatusCode.ERROR if status_code >= 500 else StatusCode.OK
                )
            except ImportError:
                pass

    def _record_metrics(
        self, method: str, path: str, status_code: int, duration: float
    ) -> None:
        """Record request metrics."""
        labels = {"method": method, "path": path, "status_code": str(status_code)}
        if self._request_counter:
            self._request_counter.add(1, labels)
        if self._request_duration:
            self._request_duration.record(duration, labels)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Any],
    ) -> Response:
        """Process request with tracing.

        **Refactored: 2025 - Reduced complexity from 11 to 6**
        """
        path = request.url.path

        if not self._should_trace(path):
            return await call_next(request)

        tracer = get_telemetry().get_tracer()
        method = request.method
        context = self._extract_trace_context(request)
        start_time = time.perf_counter()
        status_code = 500

        with tracer.start_as_current_span(
            f"{method} {path}", context=context, kind=_get_span_kind()
        ) as span:
            self._set_request_attributes(span, request)
            self._update_trace_context_vars()

            try:
                response = await call_next(request)
                status_code = response.status_code
                self._set_response_status(span, status_code)
                return response
            except Exception as e:
                span.record_exception(e)
                try:
                    from opentelemetry.trace import StatusCode

                    span.set_status(StatusCode.ERROR, str(e))
                except ImportError:
                    pass
                raise
            finally:
                duration = time.perf_counter() - start_time
                self._record_metrics(method, path, status_code, duration)


def _get_span_kind() -> Any:
    """Get SpanKind.SERVER or None if not available."""
    try:
        from opentelemetry.trace import SpanKind

        return SpanKind.SERVER
    except ImportError:
        return None
