"""JWT error classes.

**Feature: full-codebase-review-2025, Task 1.3: Refactor jwt.py**
**Validates: Requirements 9.2**
"""

from my_app.core.errors import AuthenticationError


class TokenExpiredError(AuthenticationError):
    """Raised when a token has expired."""

    def __init__(self, message: str = "Token has expired") -> None:
        super().__init__(message=message)
        self.error_code = "TOKEN_EXPIRED"


class TokenInvalidError(AuthenticationError):
    """Raised when a token is invalid or malformed."""

    def __init__(self, message: str = "Invalid token") -> None:
        super().__init__(message=message)
        self.error_code = "TOKEN_INVALID"


class TokenRevokedError(AuthenticationError):
    """Raised when a token has been revoked."""

    def __init__(self, message: str = "Token has been revoked") -> None:
        super().__init__(message=message)
        self.error_code = "TOKEN_REVOKED"
