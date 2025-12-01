"""Secrets manager exceptions.

**Feature: code-review-refactoring, Task 18.1: Refactor secrets_manager.py**
**Validates: Requirements 5.7**
"""


class SecretsError(Exception):
    """Base secrets error."""

    def __init__(self, message: str, error_code: str = "SECRETS_ERROR") -> None:
        super().__init__(message)
        self.error_code = error_code


class SecretNotFoundError(SecretsError):
    """Secret not found error."""

    def __init__(self, secret_name: str) -> None:
        super().__init__(f"Secret not found: {secret_name}", "SECRET_NOT_FOUND")
        self.secret_name = secret_name


class SecretAccessDeniedError(SecretsError):
    """Secret access denied error."""

    def __init__(self, secret_name: str) -> None:
        super().__init__(f"Access denied to secret: {secret_name}", "SECRET_ACCESS_DENIED")
        self.secret_name = secret_name


class SecretRotationError(SecretsError):
    """Secret rotation error."""

    def __init__(self, secret_name: str, reason: str) -> None:
        super().__init__(f"Rotation failed for {secret_name}: {reason}", "SECRET_ROTATION_ERROR")
        self.secret_name = secret_name
