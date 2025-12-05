"""Access denied error.

Raised when access to a resource is forbidden.

**Feature: python-api-base-2025-state-of-art**
"""

from application.common.errors.base.application_error import ApplicationError


class ForbiddenError(ApplicationError):
    """Access denied error.

    Raised when a user is authenticated but does not have permission
    to access the requested resource.

    Example:
        >>> raise ForbiddenError("You do not have permission to access this resource")
    """

    def __init__(self, message: str = "Access denied") -> None:
        """Initialize forbidden error.

        Args:
            message: Error message describing the access denial.
        """
        super().__init__(message=message, code="FORBIDDEN")
