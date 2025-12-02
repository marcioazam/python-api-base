"""Prometheus middleware for FastAPI.

**Feature: observability-infrastructure**
**Requirement: R5 - Prometheus Metrics**
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from infrastructure.prometheus.registry import MetricsRegistry, get_registry

if TYPE_CHECKING:
    from starlette.types import ASGIApp


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP request metrics.

    Collects:
    - http_requests_total: Counter of total requests
    - http_request_duration_seconds: Histogram of request durations
    - http_requests_in_progress: Gauge of active requests

    **Feature: observability-infrastructure**
    **Requirement: R5.3 - HTTP Metrics Middleware**

    Example:
        >>> app.add_middleware(PrometheusMiddleware)
    """

    def __init__(
        self,
        app: ASGIApp,
        registry: MetricsRegistry | None = None,
        skip_paths: list[str] | None = None,
    ) -> None:
        """Initialize middleware.

        Args:
            app: ASGI application
            registry: Metrics registry (uses global if not provided)
            skip_paths: Paths to skip from metrics collection
        """
        super().__init__(app)
        self._registry = registry or get_registry()
        self._skip_paths = set(skip_paths or ["/metrics", "/health", "/ready"])

        # Create metrics
        self._requests_total = self._registry.counter(
            "http_requests_total",
            "Total HTTP requests",
            labels=["method", "endpoint", "status"],
        )

        self._request_duration = self._registry.histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            labels=["method", "endpoint"],
        )

        self._requests_in_progress = self._registry.gauge(
            "http_requests_in_progress",
            "HTTP requests currently in progress",
            labels=["method", "endpoint"],
        )

    def _get_endpoint(self, request: Request) -> str:
        """Get normalized endpoint for metrics.

        Args:
            request: HTTP request

        Returns:
            Endpoint path (uses route pattern if available)
        """
        # Try to get the route pattern for better grouping
        if hasattr(request, "scope") and "route" in request.scope:
            route = request.scope["route"]
            if hasattr(route, "path"):
                return route.path

        return request.url.path

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and collect metrics.

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response
        """
        # Skip metrics collection for certain paths
        if request.url.path in self._skip_paths:
            return await call_next(request)

        method = request.method
        endpoint = self._get_endpoint(request)

        # Track in-progress requests
        self._requests_in_progress.labels(method=method, endpoint=endpoint).inc()
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            status = str(response.status_code)
        except Exception:
            status = "500"
            raise
        finally:
            # Record duration
            duration = time.perf_counter() - start_time
            self._request_duration.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)

            # Record request count
            self._requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status,
            ).inc()

            # Decrement in-progress
            self._requests_in_progress.labels(
                method=method,
                endpoint=endpoint,
            ).dec()

        return response
