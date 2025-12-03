"""API middleware components.

This module provides middleware for request processing including
security headers, rate limiting, request logging, and error handling.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 13, 16, 18, 19, 22**

Import individual modules directly to avoid circular imports:
    from interface.middleware.security import SecurityHeadersMiddleware, CORSManager
    from interface.middleware.logging import RequestLoggingMiddleware
    from interface.middleware.request import RequestIdMiddleware
    from interface.middleware.production import setup_production_middleware
"""

# Security middleware
from interface.middleware.security import (
    CORSManager,
    CORSPolicy,
    SecurityHeadersMiddleware,
)

# Request processing middleware
from interface.middleware.request import (
    RequestIDMiddleware,
    RequestSizeLimitMiddleware,
    TimeoutConfig,
    TimeoutMiddleware,
)

# Logging middleware
from interface.middleware.logging import (
    RequestLoggerMiddleware,
    app_exception_handler,
    create_problem_detail,
    register_exception_handlers,
)

# Production middleware
from interface.middleware.production import (
    AuditConfig,
    AuditMiddleware,
    FeatureFlagMiddleware,
    MultitenancyConfig,
    MultitenancyMiddleware,
    ResilienceConfig,
    ResilienceMiddleware,
    is_feature_enabled,
    setup_production_middleware,
)

__all__ = [
    # Security
    "SecurityHeadersMiddleware",
    "CORSManager",
    "CORSPolicy",
    # Request
    "RequestIDMiddleware",
    "RequestSizeLimitMiddleware",
    "TimeoutConfig",
    "TimeoutMiddleware",
    # Logging
    "RequestLoggerMiddleware",
    "app_exception_handler",
    "create_problem_detail",
    "register_exception_handlers",
    # Production
    "AuditConfig",
    "AuditMiddleware",
    "FeatureFlagMiddleware",
    "MultitenancyConfig",
    "MultitenancyMiddleware",
    "ResilienceConfig",
    "ResilienceMiddleware",
    "is_feature_enabled",
    "setup_production_middleware",
]
