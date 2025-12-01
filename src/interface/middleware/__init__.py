"""API middleware components.

This module provides middleware for request processing including
security headers, rate limiting, request logging, and error handling.

Import individual modules directly to avoid circular imports:
    from interface.middleware.security_headers import SecurityHeadersMiddleware
    from interface.middleware.cors_manager import CORSManager
    from interface.middleware.request_size_limit import RequestSizeLimitMiddleware
"""

# Lazy imports to avoid circular dependencies
__all__ = [
    "SecurityHeadersMiddleware",
    "CORSManager",
    "CORSPolicy",
    "RequestSizeLimitMiddleware",
]
