"""API middleware components.

This module provides middleware for request processing including
security headers, rate limiting, request logging, and error handling.
"""

from my_api.adapters.api.middleware.error_handler import (
    register_exception_handlers,
)
from my_api.adapters.api.middleware.rate_limiter import (
    get_rate_limit,
    limiter,
    rate_limit_exceeded_handler,
)
from my_api.adapters.api.middleware.request_id import (
    RequestIDMiddleware,
    get_request_id,
)
from my_api.adapters.api.middleware.request_logger import (
    RequestLoggerMiddleware,
)
from my_api.adapters.api.middleware.security_headers import (
    SecurityHeadersMiddleware,
)

__all__ = [
    "RequestIDMiddleware",
    "RequestLoggerMiddleware",
    "SecurityHeadersMiddleware",
    "get_rate_limit",
    "get_request_id",
    "limiter",
    "rate_limit_exceeded_handler",
    "register_exception_handlers",
]
