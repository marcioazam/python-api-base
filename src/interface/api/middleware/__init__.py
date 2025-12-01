"""API middleware components.

This module provides middleware for request processing including
security headers, rate limiting, request logging, and error handling.

Import individual modules directly to avoid circular imports:
    from src.interface.api.middleware.security_headers import SecurityHeadersMiddleware
    from src.interface.api.middleware.cors_manager import CORSManager
    from src.interface.api.middleware.request_size_limit import RequestSizeLimitMiddleware
"""

# Lazy imports to avoid circular dependencies
__all__ = [
    "SecurityHeadersMiddleware",
    "CORSManager",
    "CORSPolicy",
    "RequestSizeLimitMiddleware",
]
