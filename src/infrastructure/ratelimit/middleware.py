"""Rate limit middleware for FastAPI with PEP 695 generics.

**Feature: enterprise-generics-2025**
**Requirement: R5.5 - Generic_RateLimitMiddleware[TClient]**
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from infrastructure.ratelimit.config import RateLimit
from infrastructure.ratelimit.limiter import RateLimiter, RateLimitResult

logger = logging.getLogger(__name__)


# =============================================================================
# Client Extractor Protocol
# =============================================================================


@runtime_checkable
class ClientExtractor[TClient](Protocol):
    """Protocol for extracting client identifier from request.

    **Requirement: R5.5 - extract_client(request) returns TClient**

    Type Parameters:
        TClient: Client identifier type.
    """

    async def extract(self, request: Request) -> TClient:
        """Extract client identifier from request.

        Args:
            request: FastAPI request.

        Returns:
            Client identifier.
        """
        ...


# =============================================================================
# Built-in Extractors
# =============================================================================


class IPClientExtractor:
    """Extract client IP address from request."""

    async def extract(self, request: Request) -> str:
        """Extract client IP.

        Handles X-Forwarded-For header for proxied requests.
        """
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


class UserIdExtractor:
    """Extract user ID from authenticated request."""

    def __init__(self, user_attr: str = "user") -> None:
        """Initialize extractor.

        Args:
            user_attr: Request state attribute containing user.
        """
        self._user_attr = user_attr

    async def extract(self, request: Request) -> str:
        """Extract user ID from request state."""
        user = getattr(request.state, self._user_attr, None)
        if user is None:
            # Fallback to IP if not authenticated
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                return f"anon:{forwarded.split(',')[0].strip()}"
            return f"anon:{request.client.host if request.client else 'unknown'}"

        # Try common user ID attributes
        for attr in ("id", "user_id", "sub", "email"):
            if hasattr(user, attr):
                return str(getattr(user, attr))

        return str(user)


class APIKeyExtractor:
    """Extract API key from request header."""

    def __init__(self, header_name: str = "X-API-Key") -> None:
        """Initialize extractor.

        Args:
            header_name: Header containing API key.
        """
        self._header = header_name

    async def extract(self, request: Request) -> str:
        """Extract API key from header."""
        api_key = request.headers.get(self._header)
        if api_key:
            return f"key:{api_key[:8]}..."  # Truncate for privacy
        return "no-key"


# =============================================================================
# Rate Limit Middleware
# =============================================================================


class RateLimitMiddleware[TClient](BaseHTTPMiddleware):
    """Generic rate limit middleware for FastAPI.

    **Requirement: R5.5 - Generic_RateLimitMiddleware[TClient]**

    Type Parameters:
        TClient: Client identifier type.

    Example:
        ```python
        app = FastAPI()

        limiter = SlidingWindowLimiter[str](config)
        extractor = IPClientExtractor()

        app.add_middleware(
            RateLimitMiddleware[str],
            limiter=limiter,
            extractor=extractor,
        )
        ```
    """

    def __init__(
        self,
        app: Any,
        limiter: RateLimiter[TClient],
        extractor: ClientExtractor[TClient],
        endpoint_limits: dict[str, RateLimit] | None = None,
        exclude_paths: set[str] | None = None,
        on_rate_limited: Callable[[RateLimitResult[TClient]], Awaitable[Response]]
        | None = None,
    ) -> None:
        """Initialize middleware.

        Args:
            app: FastAPI application.
            limiter: Rate limiter instance.
            extractor: Client extractor.
            endpoint_limits: Per-endpoint rate limits.
            exclude_paths: Paths to exclude from rate limiting.
            on_rate_limited: Custom handler for rate limited requests.
        """
        super().__init__(app)
        self._limiter = limiter
        self._extractor = extractor
        self._exclude_paths = exclude_paths or {
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
        }
        self._on_rate_limited = on_rate_limited

        if endpoint_limits:
            self._limiter.configure(endpoint_limits)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process request through rate limiter.

        Args:
            request: FastAPI request.
            call_next: Next middleware/handler.

        Returns:
            Response with rate limit headers.
        """
        # Skip excluded paths
        if request.url.path in self._exclude_paths:
            return await call_next(request)

        # Extract client identifier
        try:
            client = await self._extractor.extract(request)
        except Exception as e:
            logger.warning(f"Failed to extract client: {e}")
            return await call_next(request)

        # Get endpoint-specific limit
        endpoint = self._get_endpoint_key(request)
        limit = self._limiter.get_limit(endpoint)

        # Check rate limit
        result = await self._limiter.check(client, limit, endpoint)

        if not result.is_allowed:
            return await self._handle_rate_limited(result)

        # Process request and add headers
        response = await call_next(request)

        # Add rate limit headers
        for key, value in result.headers.items():
            response.headers[key] = value

        return response

    def _get_endpoint_key(self, request: Request) -> str:
        """Get endpoint key for rate limit lookup.

        Args:
            request: FastAPI request.

        Returns:
            Endpoint key string.
        """
        # Use method + path pattern
        path = request.url.path.rstrip("/")

        # Simplify path by removing IDs
        # /api/v1/users/123 -> /api/v1/users/*
        parts = path.split("/")
        normalized = []
        for part in parts:
            if part.isdigit() or self._is_uuid(part):
                normalized.append("*")
            else:
                normalized.append(part)

        return f"{request.method}:{'/'.join(normalized)}"

    @staticmethod
    def _is_uuid(value: str) -> bool:
        """Check if value looks like a UUID."""
        return len(value) == 36 and value.count("-") == 4

    async def _handle_rate_limited(
        self,
        result: RateLimitResult[TClient],
    ) -> Response:
        """Handle rate limited request.

        Args:
            result: Rate limit result.

        Returns:
            429 Too Many Requests response.
        """
        if self._on_rate_limited:
            return await self._on_rate_limited(result)

        return JSONResponse(
            status_code=429,
            content={
                "type": "https://httpstatuses.com/429",
                "title": "Too Many Requests",
                "status": 429,
                "detail": f"Rate limit exceeded. Retry after {result.retry_after.total_seconds():.0f} seconds."
                if result.retry_after
                else "Rate limit exceeded.",
                "instance": f"/ratelimit/{result.client}",
            },
            headers=result.headers,
        )


# =============================================================================
# Decorator for Route-Level Rate Limiting
# =============================================================================


def rate_limit[TClient](
    limiter: RateLimiter[TClient],
    limit: RateLimit,
    extractor: ClientExtractor[TClient] | None = None,
) -> Callable:
    """Decorator for route-level rate limiting.

    **Requirement: R5.6 - Per-endpoint limits**

    Type Parameters:
        TClient: Client identifier type.

    Args:
        limiter: Rate limiter instance.
        limit: Rate limit to apply.
        extractor: Optional client extractor (defaults to IP).

    Returns:
        Route decorator.

    Example:
        ```python
        @app.post("/upload")
        @rate_limit(limiter, RateLimit(5, timedelta(minutes=1)))
        async def upload_file(file: UploadFile): ...
        ```
    """
    from functools import wraps
    from fastapi import HTTPException

    _extractor = extractor or IPClientExtractor()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request in args
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            for value in kwargs.values():
                if isinstance(value, Request):
                    request = value
                    break

            if request is None:
                return await func(*args, **kwargs)

            client = await _extractor.extract(request)
            result = await limiter.check(client, limit, func.__name__)

            if not result.is_allowed:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Retry after {result.retry_after.total_seconds():.0f}s"
                    if result.retry_after
                    else "Rate limit exceeded.",
                    headers=result.headers,
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
