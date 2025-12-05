"""Resource conflict error.

Raised when a resource conflict occurs (e.g., duplicate key).

**Feature: python-api-base-2025-state-of-art**
"""

from application.common.errors.base.application_error import ApplicationError


class ConflictError(ApplicationError):
    """Resource conflict error (e.g., duplicate key).

    Raised when there is a conflict with an existing resource,
    such as attempting to create a duplicate entity.

    Example:
        >>> raise ConflictError(
        ...     message="User with email already exists",
        ...     resource="User"
        ... )
    """

    def __init__(self, message: str, resource: str | None = None) -> None:
        """Initialize conflict error.

        Args:
            message: Error message describing the conflict.
            resource: Type of resource involved in the conflict.
        """
        super().__init__(
            message=message,
            code="CONFLICT",
            details={"resource": resource} if resource else {},
        )
