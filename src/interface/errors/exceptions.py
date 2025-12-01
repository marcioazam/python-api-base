"""Exception hierarchy for interface layer.

This module provides a structured exception hierarchy for the interface layer,
with specific exceptions for common error scenarios.

**Feature: interface-layer-generics-review**
"""

from __future__ import annotations


class InterfaceError(Exception):
    """Base exception for interface layer.

    All interface-specific exceptions should inherit from this class.
    """

    pass


class FieldError:
    """Field-level validation error.

    Args:
        field: Field name that failed validation
        message: Human-readable error message
        code: Machine-readable error code
    """

    def __init__(self, field: str, message: str, code: str) -> None:
        """Initialize field error.

        Args:
            field: Field name
            message: Error message
            code: Error code
        """
        self.field = field
        self.message = message
        self.code = code

    def __repr__(self) -> str:
        """String representation of field error."""
        return f"FieldError(field='{self.field}', message='{self.message}', code='{self.code}')"

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "field": self.field,
            "message": self.message,
            "code": self.code,
        }


class ValidationError(InterfaceError):
    """Validation failed with field-level errors.

    Args:
        errors: List of field validation errors
    """

    def __init__(self, errors: list[FieldError]) -> None:
        """Initialize validation error.

        Args:
            errors: List of field-level validation errors
        """
        self.errors = errors
        super().__init__(f"Validation failed: {len(errors)} errors")


class NotFoundError(InterfaceError):
    """Resource not found.

    Args:
        resource: Type of resource
        id: Resource identifier
    """

    def __init__(self, resource: str, id: str) -> None:
        """Initialize not found error.

        Args:
            resource: Resource type
            id: Resource identifier
        """
        self.resource = resource
        self.id = id
        super().__init__(f"{resource} '{id}' not found")


class UnwrapError(InterfaceError):
    """Attempted to unwrap an Err result.

    This exception is raised when trying to extract a value from
    an Err result using the unwrap() method.
    """

    pass


class BuilderValidationError(InterfaceError):
    """Builder validation failed.

    Args:
        missing_fields: List of required fields that are missing or validation errors
    """

    def __init__(self, missing_fields: list[str]) -> None:
        """Initialize builder validation error.

        Args:
            missing_fields: List of missing required fields or validation errors
        """
        self.missing_fields = missing_fields
        super().__init__(f"Builder validation failed: {missing_fields}")


class InvalidStatusTransitionError(InterfaceError):
    """Invalid status transition attempted.

    Args:
        from_status: Current status
        to_status: Target status
    """

    def __init__(self, from_status: str, to_status: str) -> None:
        """Initialize invalid transition error.

        Args:
            from_status: Current status
            to_status: Target status
        """
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f"Cannot transition from {from_status} to {to_status}")


class TransformationError(InterfaceError):
    """Data transformation failed.

    Args:
        transformer: Name of the transformer
        reason: Reason for failure
    """

    def __init__(self, transformer: str, reason: str) -> None:
        """Initialize transformation error.

        Args:
            transformer: Transformer name
            reason: Failure reason
        """
        self.transformer = transformer
        self.reason = reason
        super().__init__(f"Transformation failed in {transformer}: {reason}")


class ConfigurationError(InterfaceError):
    """Configuration is invalid or missing.

    Args:
        component: Component with configuration issue
        issue: Description of the issue
    """

    def __init__(self, component: str, issue: str) -> None:
        """Initialize configuration error.

        Args:
            component: Component name
            issue: Issue description
        """
        self.component = component
        self.issue = issue
        super().__init__(f"Configuration error in {component}: {issue}")


class CompositionError(InterfaceError):
    """API composition failed.

    Args:
        call_name: Name of the failed call
        reason: Reason for failure
    """

    def __init__(self, call_name: str, reason: str) -> None:
        """Initialize composition error.

        Args:
            call_name: Name of the failed call
            reason: Failure reason
        """
        self.call_name = call_name
        self.reason = reason
        super().__init__(f"Composition failed for '{call_name}': {reason}")


class RepositoryError(InterfaceError):
    """Repository operation failed.

    Args:
        operation: Operation that failed
        reason: Reason for failure
        cause: Original exception if any
    """

    def __init__(
        self, operation: str, reason: str, cause: Exception | None = None
    ) -> None:
        """Initialize repository error.

        Args:
            operation: Operation name
            reason: Failure reason
            cause: Original exception
        """
        self.operation = operation
        self.reason = reason
        self.cause = cause
        super().__init__(f"Repository {operation} failed: {reason}")


class ServiceError(InterfaceError):
    """Service operation failed.

    Args:
        operation: Operation that failed
        reason: Reason for failure
        field_errors: Optional field-level errors
    """

    def __init__(
        self, operation: str, reason: str, field_errors: list[FieldError] | None = None
    ) -> None:
        """Initialize service error.

        Args:
            operation: Operation name
            reason: Failure reason
            field_errors: Optional field-level errors
        """
        self.operation = operation
        self.reason = reason
        self.field_errors = field_errors or []
        super().__init__(f"Service {operation} failed: {reason}")
