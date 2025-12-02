"""Logging middleware for HTTP request instrumentation with structlog.

Integrates correlation ID propagation with structured logging,
ensuring all logs within a request context include tracing information.

**Feature: observability-infrastructure**
**Requirement: R1 - Structured Logging Infrastructure**
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from infrastructure.observability.correlation_id import (
    CorrelationConfig,
    CorrelationContext,
    CorrelationContextManager,
    CorrelationService,
)

if TYPE_CHECKING:
    from collections.abc import Callable


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that integrates correlation IDs with structured logging.

    Features:
    - Extracts or generates correlation ID from request headers
    - Binds correlation context to structlog for all logs in request
    - Adds correlation ID to response headers
    - Logs request start/end with duration

    **Feature: observability-infrastructure**
    **Requirement: R1, R2 - Structured Logging**

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> app.add_middleware(LoggingMiddleware)
    """

    def __init__(
        self,
        app: Any,
        service_name: str = "python-api-base",
        excluded_paths: list[str] | None = None,
        log_request_body: bool = False,
        log_response_body: bool = False,
    ) -> None:
        """Initialize logging middleware.

        Args:
            app: ASGI application
            service_name: Service name for log context
            excluded_paths: Paths to exclude from logging (e.g., health checks)
            log_request_body: Whether to log request body (careful with PII)
            log_response_body: Whether to log response body
        """
        super().__init__(app)
        self._service_name = service_name
        self._excluded_paths = set(
            excluded_paths or ["/health/live", "/health/ready", "/metrics"]
        )
        self._log_request_body = log_request_body
        self._log_response_body = log_response_body
        self._correlation_service = CorrelationService(
            CorrelationConfig(
                service_name=service_name,
                generate_if_missing=True,
                propagate_to_response=True,
            )
        )
        self._logger = structlog.get_logger("http")

    def _should_log(self, path: str) -> bool:
        """Check if the path should be logged."""
        return path not in self._excluded_paths

    def _extract_client_info(self, request: Request) -> dict[str, Any]:
        """Extract client information from request."""
        client = request.client
        return {
            "client_ip": client.host if client else "unknown",
            "client_port": client.port if client else 0,
            "user_agent": request.headers.get("user-agent", ""),
        }

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Any],
    ) -> Response:
        """Process request with logging and correlation context.

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response with correlation headers
        """
        path = request.url.path
        method = request.method

        # Skip logging for excluded paths but still propagate correlation
        should_log = self._should_log(path)

        # Extract or create correlation context
        headers = dict(request.headers)
        context = self._correlation_service.extract_from_headers(headers)

        # Bind context to structlog
        with CorrelationContextManager(context, self._service_name):
            # Also bind to structlog contextvars
            structlog.contextvars.clear_contextvars()
            structlog.contextvars.bind_contextvars(
                correlation_id=context.correlation_id,
                request_id=context.request_id,
                method=method,
                path=path,
            )

            start_time = time.perf_counter()
            status_code = 500  # Default for errors

            try:
                # Log request start
                if should_log:
                    self._log_request_start(request, context)

                # Process request
                response = await call_next(request)
                status_code = response.status_code

                # Add correlation headers to response
                response_headers = self._correlation_service.get_response_headers(
                    context
                )
                for header_name, header_value in response_headers.items():
                    response.headers[header_name] = header_value

                return response

            except Exception as exc:
                # Log exception
                self._logger.exception(
                    "request_failed",
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                raise

            finally:
                # Calculate duration
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Log request completion
                if should_log:
                    self._log_request_end(
                        method=method,
                        path=path,
                        status_code=status_code,
                        duration_ms=duration_ms,
                    )

    def _log_request_start(
        self,
        request: Request,
        context: CorrelationContext,
    ) -> None:
        """Log request start."""
        client_info = self._extract_client_info(request)

        log_data: dict[str, Any] = {
            "url": str(request.url),
            "query_params": dict(request.query_params),
            **client_info,
        }

        self._logger.info("request_started", **log_data)

    def _log_request_end(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        """Log request completion."""
        log_level = "info"
        if status_code >= 500:
            log_level = "error"
        elif status_code >= 400:
            log_level = "warning"

        log_func = getattr(self._logger, log_level)
        log_func(
            "request_completed",
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
        )


def create_logging_middleware(
    service_name: str = "python-api-base",
    excluded_paths: list[str] | None = None,
) -> type[LoggingMiddleware]:
    """Factory to create configured LoggingMiddleware class.

    Args:
        service_name: Service name for log context
        excluded_paths: Paths to exclude from logging

    Returns:
        Configured LoggingMiddleware class

    Example:
        >>> middleware_class = create_logging_middleware(
        ...     service_name="my-api",
        ...     excluded_paths=["/health", "/metrics"],
        ... )
        >>> app.add_middleware(middleware_class)
    """

    class ConfiguredLoggingMiddleware(LoggingMiddleware):
        def __init__(self, app: Any) -> None:
            super().__init__(
                app,
                service_name=service_name,
                excluded_paths=excluded_paths,
            )

    return ConfiguredLoggingMiddleware
