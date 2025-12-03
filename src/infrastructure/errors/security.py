"""Security-related infrastructure exceptions.

**Feature: infrastructure-code-review**
**Validates: Requirements 8.2, 10.3**
"""

from infrastructure.errors.base import InfrastructureError


class TokenStoreError(InfrastructureError):
    """Token storage error.

    Raised when token storage operations fail.
    """

    pass


class TokenValidationError(TokenStoreError):
    """Token validation error.

    Raised when token validation fails due to invalid format,
    expiration, or signature verification failure.
    """

    pass


class AuditLogError(InfrastructureError):
    """Audit logging error.

    Raised when audit log operations fail.
    """

    pass
