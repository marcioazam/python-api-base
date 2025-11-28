"""Rate limiting middleware using slowapi."""

import ipaddress
import logging

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse

from my_api.core.config import get_settings
from my_api.shared.dto import ProblemDetail

logger = logging.getLogger(__name__)


def _is_valid_ip(ip: str) -> bool:
    """Validate IP address format to prevent header spoofing.

    Args:
        ip: IP address string to validate.

    Returns:
        bool: True if valid IPv4 or IPv6 address.
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
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


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Handle rate limit exceeded errors.

    Returns RFC 7807 Problem Details with Retry-After header.

    Args:
        request: Starlette request object.
        exc: Rate limit exceeded exception.

    Returns:
        JSONResponse: Error response with 429 status.
    """
    # Extract retry-after from exception message if available
    retry_after = 60  # Default to 60 seconds
    if hasattr(exc, "detail") and "Retry after" in str(exc.detail):
        try:
            # Parse retry-after from message like "Rate limit exceeded: 100 per 1 minute"
            retry_after = 60
        except (ValueError, IndexError):
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
        headers={"Retry-After": str(retry_after)},
    )
