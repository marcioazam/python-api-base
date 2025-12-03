"""Database-related infrastructure exceptions.

**Feature: infrastructure-code-review**
**Validates: Requirements 8.2, 10.3**
"""

from infrastructure.errors.base import InfrastructureError


class DatabaseError(InfrastructureError):
    """Database operation error.

    Raised when database operations fail due to connection issues,
    query errors, or constraint violations.
    """

    pass


class ConnectionPoolError(DatabaseError):
    """Connection pool error.

    Raised when connection pool operations fail, such as
    pool exhaustion or connection acquisition timeout.
    """

    pass
