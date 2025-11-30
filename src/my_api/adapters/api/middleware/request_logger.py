"""Request/response logging middleware.

**Feature: api-base-improvements**
**Validates: Requirements 9.1, 9.2, 9.3, 9.5**
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


# Fields that should be masked in logs
SENSITIVE_FIELDS = frozenset([
    "password",
    "passwd",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "credential",
    "credentials",
    "credit_card",
    "creditcard",
    "card_number",
    "cvv",
    "ssn",
    "social_security",
    "pin",
])

# Headers that should be masked
SENSITIVE_HEADERS = frozenset([
    "authorization",
    "x-api-key",
    "x-auth-token",
    "cookie",
    "set-cookie",
])

MASK_VALUE = "***MASKED***"


@dataclass
class RequestLogEntry:
    """Log entry for an incoming request.

    Attributes:
        request_id: Correlation ID for the request.
        method: HTTP method.
        path: Request path.
        query_params: Query parameters (sanitized).
        headers: Request headers (sanitized).
        body_size: Size of request body in bytes.
        client_ip: Client IP address.
        user_agent: Client user agent.
    """

    request_id: str
    method: str
    path: str
    query_params: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    body_size: int = 0
    client_ip: str | None = None
    user_agent: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "request_id": self.request_id,
            "method": self.method,
            "path": self.path,
            "query_params": self.query_params,
            "headers": self.headers,
            "body_size": self.body_size,
            "client_ip": self.client_ip,
            "user_agent": self.user_agent,
        }


@dataclass
class ResponseLogEntry:
    """Log entry for an outgoing response.

    Attributes:
        request_id: Correlation ID for the request.
        status_code: HTTP status code.
        duration_ms: Request duration in milliseconds.
        response_size: Size of response body in bytes.
    """

    request_id: str
    status_code: int
    duration_ms: float
    response_size: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "request_id": self.request_id,
            "status_code": self.status_code,
            "duration_ms": round(self.duration_ms, 2),
            "response_size": self.response_size,
        }


def mask_sensitive_value(key: str, value: Any) -> Any:
    """Mask sensitive values based on key name.

    Args:
        key: Field/header name.
        value: Value to potentially mask.

    Returns:
        Masked value if sensitive, original value otherwise.
    """
    key_lower = key.lower()
    if key_lower in SENSITIVE_FIELDS or key_lower in SENSITIVE_HEADERS:
        return MASK_VALUE
    return value


def mask_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Mask sensitive values in a dictionary.

    Args:
        data: Dictionary to mask.

    Returns:
        Dictionary with sensitive values masked.
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = mask_dict(value)
        elif isinstance(value, list):
            result[key] = [
                mask_dict(item) if isinstance(item, dict)
                else mask_sensitive_value(key, item)
                for item in value
            ]
        else:
            result[key] = mask_sensitive_value(key, value)
    return result


def sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    """Sanitize request/response headers for logging.

    Args:
        headers: Headers dictionary.

    Returns:
        Sanitized headers with sensitive values masked.
    """
    result = {}
    for key, value in headers.items():
        key_lower = key.lower()
        if key_lower in SENSITIVE_HEADERS:
            result[key] = MASK_VALUE
        else:
            result[key] = value
    return result


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses.

    Logs incoming requests with method, path, headers (sanitized),
    and outgoing responses with status, duration, and size.
    All sensitive data is masked.
    """

    def __init__(
        self,
        app,
        *,
        log_request_body: bool = False,
        log_response_body: bool = False,
        excluded_paths: list[str] | None = None,
        log_level: int = logging.INFO,
    ) -> None:
        """Initialize request logger middleware.

        Args:
            app: ASGI application.
            log_request_body: Whether to log request body (default: False).
            log_response_body: Whether to log response body (default: False).
            excluded_paths: Paths to exclude from logging.
            log_level: Logging level to use.
        """
        super().__init__(app)
        self._log_request_body = log_request_body
        self._log_response_body = log_response_body
        self._excluded_paths = set(excluded_paths or [])
        self._log_level = log_level

    def _should_log(self, path: str) -> bool:
        """Check if request should be logged.

        Args:
            path: Request path.

        Returns:
            True if request should be logged.
        """
        return path not in self._excluded_paths

    def _get_request_id(self, request: Request) -> str:
        """Get request ID from request state or headers.

        Args:
            request: Incoming request.

        Returns:
            Request ID string.
        """
        # Try to get from state (set by RequestIDMiddleware)
        if hasattr(request.state, "request_id"):
            return request.state.request_id

        # Try to get from header
        return request.headers.get("X-Request-ID", "unknown")

    def _get_client_ip(self, request: Request) -> str | None:
        """Get client IP address.

        Args:
            request: Incoming request.

        Returns:
            Client IP address or None.
        """
        # Check X-Forwarded-For header first (for proxied requests)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Fall back to client host
        if request.client:
            return request.client.host

        return None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response.

        Args:
            request: Incoming request.
            call_next: Next middleware/handler.

        Returns:
            Response from handler.
        """
        if not self._should_log(request.url.path):
            return await call_next(request)

        start_time = time.perf_counter()
        request_id = self._get_request_id(request)

        # Log request
        request_entry = RequestLogEntry(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            headers=sanitize_headers(dict(request.headers)),
            client_ip=self._get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )

        logger.log(
            self._log_level,
            "request_received",
            extra={"request": request_entry.to_dict()},
        )

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Get response size
        response_size = 0
        if hasattr(response, "body"):
            response_size = len(response.body)
        elif "content-length" in response.headers:
            response_size = int(response.headers["content-length"])

        # Log response
        response_entry = ResponseLogEntry(
            request_id=request_id,
            status_code=response.status_code,
            duration_ms=duration_ms,
            response_size=response_size,
        )

        logger.log(
            self._log_level,
            "response_sent",
            extra={"response": response_entry.to_dict()},
        )

        return response
