"""API middleware components.

This module provides middleware for request processing including
security headers, rate limiting, request logging, and error handling.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 13, 16, 18, 19, 22**

Import individual modules directly to avoid circular imports:
    from interface.middleware.security_headers import SecurityHeadersMiddleware
    from interface.middleware.cors_manager import CORSManager
    from interface.middleware.production import setup_production_middleware
"""

# Lazy imports to avoid circular dependencies
__all__ = [
    # Core middleware
    "SecurityHeadersMiddleware",
    "CORSManager",
    "CORSPolicy",
    "RequestSizeLimitMiddleware",
    # Production middleware (Req 13, 16, 18, 19, 22)
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
