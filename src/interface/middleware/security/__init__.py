"""Security middleware components.

**Feature: api-architecture-analysis**
**Validates: Requirements 5.3**
"""

from interface.middleware.security.cors_manager import CORSManager, CORSPolicy
from interface.middleware.security.security_headers import SecurityHeadersMiddleware

__all__ = [
    "CORSManager",
    "CORSPolicy",
    "SecurityHeadersMiddleware",
]
