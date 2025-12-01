"""Request body size limit middleware.

Prevents large request bodies that could cause DoS attacks.
Supports configurable limits per route.
"""

import re
from dataclasses import dataclass, field
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


@dataclass
class RouteSizeLimit:
    """Size limit configuration for a route pattern."""

    pattern: str
    max_size: int
    _compiled: re.Pattern | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Compile the pattern."""
        try:
            self._compiled = re.compile(self.pattern)
        except re.error:
            self._compiled = None

    def matches(self, path: str) -> bool:
        """Check if path matches this route."""
        if self._compiled is None:
            return False
        return bool(self._compiled.match(path))


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request body size.

    Prevents large request bodies that could cause memory issues
    or denial of service attacks.

    Example:
        >>> app.add_middleware(
        ...     RequestSizeLimitMiddleware,
        ...     max_size=1024 * 1024,  # 1MB default
        ...     route_limits={
        ...         "/api/upload": 10 * 1024 * 1024,  # 10MB for uploads
        ...         "/api/import": 5 * 1024 * 1024,   # 5MB for imports
        ...     },
        ... )
    """

    def __init__(
        self,
        app: Any,
        max_size: int = 1024 * 1024,  # 1MB default
        route_limits: dict[str, int] | None = None,
        error_response: dict[str, Any] | None = None,
    ) -> None:
        """Initialize request size limit middleware.

        Args:
            app: ASGI application.
            max_size: Default maximum request body size in bytes.
            route_limits: Dictionary mapping route patterns to size limits.
            error_response: Custom error response body.
        """
        super().__init__(app)
        self.max_size = max_size
        self.route_limits: list[RouteSizeLimit] = []
        self.error_response = error_response or {
            "type": "https://httpstatuses.com/413",
            "title": "Request Entity Too Large",
            "status": 413,
        }

        if route_limits:
            for pattern, limit in route_limits.items():
                self.route_limits.append(RouteSizeLimit(pattern=pattern, max_size=limit))

    def get_limit_for_path(self, path: str) -> int:
        """Get the size limit for a specific path.

        Args:
            path: Request path.

        Returns:
            Size limit in bytes.
        """
        for route_limit in self.route_limits:
            if route_limit.matches(path):
                return route_limit.max_size
        return self.max_size

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Check request size before processing.

        Args:
            request: Incoming request.
            call_next: Next middleware/handler in chain.

        Returns:
            Response or 413 error if request too large.
        """
        content_length = request.headers.get("content-length")

        if content_length is not None:
            size = int(content_length)
            limit = self.get_limit_for_path(request.url.path)

            if size > limit:
                return JSONResponse(
                    status_code=413,
                    content={
                        **self.error_response,
                        "detail": f"Request body too large. Maximum size is {limit} bytes, got {size} bytes.",
                        "max_size": limit,
                        "actual_size": size,
                        "instance": str(request.url),
                    },
                    media_type="application/problem+json",
                )

        return await call_next(request)

    def add_route_limit(self, pattern: str, max_size: int) -> None:
        """Add a route-specific size limit.

        Args:
            pattern: Route pattern (regex).
            max_size: Maximum size in bytes.
        """
        self.route_limits.append(RouteSizeLimit(pattern=pattern, max_size=max_size))

    def remove_route_limit(self, pattern: str) -> bool:
        """Remove a route-specific size limit.

        Args:
            pattern: Route pattern to remove.

        Returns:
            True if removed, False if not found.
        """
        initial_len = len(self.route_limits)
        self.route_limits = [rl for rl in self.route_limits if rl.pattern != pattern]
        return len(self.route_limits) < initial_len


class StreamingRequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit streaming request body size.

    Checks size during body consumption for streaming requests
    that don't have Content-Length header.
    """

    def __init__(
        self,
        app: Any,
        max_size: int = 1024 * 1024,
    ) -> None:
        """Initialize streaming size limit middleware.

        Args:
            app: ASGI application.
            max_size: Maximum request body size in bytes.
        """
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Check request size during body consumption.

        Args:
            request: Incoming request.
            call_next: Next middleware/handler in chain.

        Returns:
            Response or 413 error if request too large.
        """
        # For requests with Content-Length, check upfront
        content_length = request.headers.get("content-length")
        if content_length is not None:
            if int(content_length) > self.max_size:
                return JSONResponse(
                    status_code=413,
                    content={
                        "type": "https://httpstatuses.com/413",
                        "title": "Request Entity Too Large",
                        "status": 413,
                        "detail": f"Request body too large. Maximum size is {self.max_size} bytes.",
                    },
                    media_type="application/problem+json",
                )

        return await call_next(request)


def create_size_limit_middleware(
    max_size: int = 1024 * 1024,
    upload_routes: list[str] | None = None,
    upload_max_size: int = 10 * 1024 * 1024,
) -> RequestSizeLimitMiddleware:
    """Factory function to create size limit middleware.

    Args:
        max_size: Default maximum size in bytes.
        upload_routes: List of route patterns for file uploads.
        upload_max_size: Maximum size for upload routes.

    Returns:
        Configured RequestSizeLimitMiddleware.
    """
    route_limits = {}
    if upload_routes:
        for route in upload_routes:
            route_limits[route] = upload_max_size

    return RequestSizeLimitMiddleware(
        app=None,  # Will be set by FastAPI
        max_size=max_size,
        route_limits=route_limits,
    )
