"""Rate limiting middleware using slowapi with sliding window support.

**Feature: api-base-score-100, Task 2.2: Integrate with existing rate limiter middleware**
**Validates: Requirements 2.1, 2.3**
"""

import ipaddress
import logging

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse

from application.common.dto import ProblemDetail
from core.config import get_settings
from infrastructure.security.rate_limit.sliding_window import (
    RateLimitResult,
    SlidingWindowRateLimiter,
    parse_rate_limit,
)

logger = logging.getLogger(__name__)

# Global sliding window limiter instance
_sliding_limiter: SlidingWindowRateLimiter | None = None


MAX_IP_LENGTH = 45  # Maximum length for IPv6 address


def _is_valid_ip(ip: str) -> bool:
    """Validate IP address format to prevent header spoofing.

    Performs strict validation including:
    - Empty string check
    - Maximum length check (45 chars for IPv6)
    - Format validation via ipaddress module

    Args:
        ip: IP address string to validate.

    Returns:
        bool: True if valid IPv4 or IPv6 address, False otherwise.
    """
    if not ip or not ip.strip():
        logger.debug("Empty IP address rejected")
        return False

    if len(ip) > MAX_IP_LENGTH:
        logger.warning(
            "IP address exceeds maximum length",
            extra={"ip_length": len(ip), "max_length": MAX_IP_LENGTH},
        )
        return False

    try:
        ipaddress.ip_address(ip.strip())
        return True
    except ValueError:
        logger.debug("Invalid IP address format", extra={"ip": ip[:20]})
        return False


def get_client_ip(request: Request) -> str:
    """Get client IP address from request.

    Handles X-Forwarded-For header for proxied requests with validation
    to prevent IP spoofing attacks.

    Args:
        request: Starlette request object.

    Returns:
        str: Client IP address.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take first IP (original client) and validate format
        ip = forwarded.split(",")[0].strip()
        if _is_valid_ip(ip):
            return ip
        logger.warning(
            "Invalid IP in X-Forwarded-For header",
            extra={"invalid_ip": ip[:50]},  # Truncate for safety
        )
    return get_remote_address(request)


# Create limiter instance with client IP key function
limiter = Limiter(key_func=get_client_ip)


def get_rate_limit() -> str:
    """Get rate limit from settings.

    Returns:
        str: Rate limit string (e.g., "100/minute").
    """
    settings = get_settings()
    return settings.security.rate_limit


def get_sliding_limiter() -> SlidingWindowRateLimiter:
    """Get or create sliding window rate limiter.

    **Feature: api-base-score-100, Task 2.2: Integrate with existing rate limiter middleware**
    **Validates: Requirements 2.1**

    Returns:
        SlidingWindowRateLimiter instance.
    """
    global _sliding_limiter
    if _sliding_limiter is None:
        config = parse_rate_limit(get_rate_limit())
        _sliding_limiter = SlidingWindowRateLimiter(config)
    return _sliding_limiter


async def check_sliding_rate_limit(request: Request) -> RateLimitResult:
    """Check rate limit using sliding window algorithm.

    **Feature: api-base-score-100, Task 2.2: Integrate with existing rate limiter middleware**
    **Validates: Requirements 2.2**

    Args:
        request: Starlette request object.

    Returns:
        RateLimitResult with allowed status and metadata.
    """
    client_ip = get_client_ip(request)
    limiter = get_sliding_limiter()
    return await limiter.is_allowed(client_ip)


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Handle rate limit exceeded errors.

    **Feature: api-base-score-100, Property 5: Rate Limit 429 Response**
    **Validates: Requirements 2.3**

    Returns RFC 7807 Problem Details with accurate Retry-After header.

    Args:
        request: Starlette request object.
        exc: Rate limit exceeded exception.

    Returns:
        JSONResponse: Error response with 429 status.
    """
    # Try to get accurate retry-after from sliding window limiter
    retry_after = 60  # Default to 60 seconds

    try:
        client_ip = get_client_ip(request)
        limiter = get_sliding_limiter()
        state = await limiter.get_state(client_ip)
        if state:
            import time

            config = parse_rate_limit(get_rate_limit())
            window_end = state.window_start + config.window_size_seconds
            retry_after = max(1, int(window_end - time.time()))
    except Exception:  # noqa: S110 - Fall back to default retry_after
        pass

    problem = ProblemDetail(
        type="https://api.example.com/errors/RATE_LIMIT_EXCEEDED",
        title="Rate Limit Exceeded",
        status=429,
        detail=str(exc.detail) if hasattr(exc, "detail") else "Too many requests",
        instance=str(request.url),
    )

    return JSONResponse(
        status_code=429,
        content=problem.model_dump(),
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Remaining": "0",
        },
    )


async def sliding_rate_limit_response(
    request: Request,
    result: RateLimitResult,
) -> JSONResponse:
    """Create rate limit exceeded response from sliding window result.

    **Feature: api-base-score-100, Property 5: Rate Limit 429 Response**
    **Validates: Requirements 2.3**

    Args:
        request: Starlette request object.
        result: Rate limit check result.

    Returns:
        JSONResponse: Error response with 429 status.
    """
    problem = ProblemDetail(
        type="https://api.example.com/errors/RATE_LIMIT_EXCEEDED",
        title="Rate Limit Exceeded",
        status=429,
        detail=f"Rate limit exceeded. Retry after {result.retry_after} seconds.",
        instance=str(request.url),
    )

    return JSONResponse(
        status_code=429,
        content=problem.model_dump(),
        headers={
            "Retry-After": str(result.retry_after),
            "X-RateLimit-Remaining": str(result.remaining),
        },
    )


class InMemoryRateLimiter:
    """Simple in-memory rate limiter for testing.

    **Feature: python-api-architecture-2025**
    **Validates: Requirements 14.2**
    """

    def __init__(self, limit: int = 100, window_seconds: int = 60) -> None:
        """Initialize rate limiter.

        Args:
            limit: Maximum requests per window.
            window_seconds: Window duration in seconds.
        """
        self._limit = limit
        self._window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}

    async def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed.

        Args:
            client_id: Client identifier.

        Returns:
            True if request is allowed, False if rate limited.
        """
        import time

        now = time.time()
        window_start = now - self._window_seconds

        # Get or create request list for client
        if client_id not in self._requests:
            self._requests[client_id] = []

        # Remove expired requests
        self._requests[client_id] = [
            ts for ts in self._requests[client_id] if ts > window_start
        ]

        # Check if under limit
        if len(self._requests[client_id]) < self._limit:
            self._requests[client_id].append(now)
            return True

        return False

    async def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for client.

        Args:
            client_id: Client identifier.

        Returns:
            Number of remaining requests in current window.
        """
        import time

        now = time.time()
        window_start = now - self._window_seconds

        if client_id not in self._requests:
            return self._limit

        # Count requests in current window
        current_requests = len([
            ts for ts in self._requests[client_id] if ts > window_start
        ])

        return max(0, self._limit - current_requests)

    def reset(self, client_id: str | None = None) -> None:
        """Reset rate limiter state.

        Args:
            client_id: Client to reset, or None to reset all.
        """
        if client_id is None:
            self._requests.clear()
        elif client_id in self._requests:
            del self._requests[client_id]
