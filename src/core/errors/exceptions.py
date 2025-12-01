"""Custom exception hierarchy for shared modules.

**Feature: shared-modules-refactoring**
**Validates: Requirements 1.3, 2.4, 10.3**

Provides a structured exception hierarchy for consistent error handling
across all shared modules.
"""

from __future__ import annotations


class SharedModuleError(Exception):
    """Base exception for all shared module errors.

    All custom exceptions in shared modules should inherit from this class
    to enable consistent error handling and filtering.
    """

    pass


class TaskExecutionError(SharedModuleError):
    """Error during background task execution.

    Attributes:
        task_id: Identifier of the failed task.
        cause: Original exception that caused the failure.
    """

    def __init__(
        self,
        task_id: str,
        message: str,
        cause: Exception | None = None,
    ) -> None:
        """Initialize task execution error.

        Args:
            task_id: Identifier of the failed task.
            message: Human-readable error message.
            cause: Original exception that caused the failure.
        """
        self.task_id = task_id
        self.cause = cause
        super().__init__(f"Task {task_id}: {message}")


class BanOperationError(SharedModuleError):
    """Error during ban operations in auto-ban system.

    Raised when ban check, record, or lift operations fail.
    """

    pass


class LockAcquisitionTimeout(SharedModuleError):
    """Lock acquisition timed out.

    Raised when a lock cannot be acquired within the specified timeout.

    Attributes:
        identifier: The identifier for which lock acquisition failed.
        timeout: The timeout duration in seconds.
    """

    def __init__(self, identifier: str, timeout: float) -> None:
        """Initialize lock acquisition timeout error.

        Args:
            identifier: The identifier for which lock acquisition failed.
            timeout: The timeout duration in seconds.
        """
        self.identifier = identifier
        self.timeout = timeout
        super().__init__(f"Lock for '{identifier}' not acquired within {timeout}s")


class RollbackError(SharedModuleError):
    """Error during rollback operation in batch processing.

    Raised when a rollback operation fails, containing both the original
    error that triggered the rollback and the error that occurred during rollback.

    Attributes:
        original_error: The exception that triggered the rollback.
        rollback_error: The exception that occurred during rollback.
    """

    def __init__(
        self,
        original_error: Exception,
        rollback_error: Exception,
    ) -> None:
        """Initialize rollback error.

        Args:
            original_error: The exception that triggered the rollback.
            rollback_error: The exception that occurred during rollback.
        """
        self.original_error = original_error
        self.rollback_error = rollback_error
        super().__init__(
            f"Rollback failed: {rollback_error} (original error: {original_error})"
        )


class ValidationError(SharedModuleError):
    """Validation error for input parameters.

    Raised when input validation fails with details about the invalid value.

    Attributes:
        field: Name of the field that failed validation.
        value: The invalid value.
        constraint: Description of the validation constraint.
    """

    def __init__(
        self,
        field: str,
        value: object,
        constraint: str,
    ) -> None:
        """Initialize validation error.

        Args:
            field: Name of the field that failed validation.
            value: The invalid value.
            constraint: Description of the validation constraint.
        """
        self.field = field
        self.value = value
        self.constraint = constraint
        super().__init__(f"Validation failed for '{field}': {constraint} (got: {value})")


# Phase 2 Module Exceptions
# **Feature: shared-modules-phase2**
# **Validates: Requirements 2.3, 6.2, 13.1, 15.3**


class Phase2ModuleError(SharedModuleError):
    """Base exception for phase 2 module errors.

    All phase 2 custom exceptions should inherit from this class.
    """

    pass


class PoolInvariantViolation(Phase2ModuleError):
    """Connection pool counter invariant violated.

    Raised when the pool's counter invariant (idle + in_use + unhealthy == total)
    is violated.

    Attributes:
        idle: Number of idle connections.
        in_use: Number of connections in use.
        unhealthy: Number of unhealthy connections.
        total: Total number of connections.
    """

    def __init__(
        self,
        idle: int,
        in_use: int,
        unhealthy: int,
        total: int,
    ) -> None:
        """Initialize pool invariant violation error.

        Args:
            idle: Number of idle connections.
            in_use: Number of connections in use.
            unhealthy: Number of unhealthy connections.
            total: Total number of connections.
        """
        self.idle = idle
        self.in_use = in_use
        self.unhealthy = unhealthy
        self.total = total
        actual_sum = idle + in_use + unhealthy
        super().__init__(
            f"Pool invariant violated: idle({idle}) + in_use({in_use}) + "
            f"unhealthy({unhealthy}) = {actual_sum}, expected total = {total}"
        )


class SnapshotIntegrityError(Phase2ModuleError):
    """Snapshot integrity check failed.

    Raised when a snapshot's state hash doesn't match the expected hash.

    Attributes:
        aggregate_id: ID of the aggregate with corrupted snapshot.
        expected_hash: Expected hash value.
        actual_hash: Actual computed hash value.
    """

    def __init__(
        self,
        aggregate_id: str,
        expected_hash: str,
        actual_hash: str,
    ) -> None:
        """Initialize snapshot integrity error.

        Args:
            aggregate_id: ID of the aggregate with corrupted snapshot.
            expected_hash: Expected hash value.
            actual_hash: Actual computed hash value.
        """
        self.aggregate_id = aggregate_id
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash
        super().__init__(
            f"Snapshot integrity check failed for aggregate '{aggregate_id}': "
            f"expected hash '{expected_hash[:16]}...', got '{actual_hash[:16]}...'"
        )


class FilterValidationError(Phase2ModuleError):
    """Filter field validation failed.

    Raised when a filter or sort field is not in the allowed list.

    Attributes:
        field: The invalid field name.
        allowed_fields: Set of allowed field names.
        operation: The operation type ('filter' or 'sort').
    """

    def __init__(
        self,
        field: str,
        allowed_fields: set[str],
        operation: str = "filter",
    ) -> None:
        """Initialize filter validation error.

        Args:
            field: The invalid field name.
            allowed_fields: Set of allowed field names.
            operation: The operation type ('filter' or 'sort').
        """
        self.field = field
        self.allowed_fields = allowed_fields
        self.operation = operation
        allowed_str = ", ".join(sorted(allowed_fields)[:10])
        if len(allowed_fields) > 10:
            allowed_str += f", ... ({len(allowed_fields) - 10} more)"
        super().__init__(
            f"Invalid {operation} field '{field}'. Allowed fields: [{allowed_str}]"
        )


class FederationValidationError(Phase2ModuleError):
    """Federation schema validation failed.

    Raised when GraphQL federation schema validation fails with one or more errors.

    Attributes:
        errors: List of validation error messages.
    """

    def __init__(self, errors: list[str]) -> None:
        """Initialize federation validation error.

        Args:
            errors: List of validation error messages.
        """
        self.errors = errors
        error_count = len(errors)
        error_summary = "; ".join(errors[:3])
        if error_count > 3:
            error_summary += f" ... and {error_count - 3} more errors"
        super().__init__(
            f"Federation schema validation failed with {error_count} error(s): {error_summary}"
        )


class EntityResolutionError(Phase2ModuleError):
    """Entity resolution failed.

    Raised when entity resolution fails due to missing resolver or invalid representation.

    Attributes:
        entity_name: Name of the entity that failed resolution.
        reason: Reason for the failure.
    """

    def __init__(self, entity_name: str, reason: str) -> None:
        """Initialize entity resolution error.

        Args:
            entity_name: Name of the entity that failed resolution.
            reason: Reason for the failure.
        """
        self.entity_name = entity_name
        self.reason = reason
        super().__init__(f"Failed to resolve entity '{entity_name}': {reason}")


# Security Module Exceptions
# **Feature: shared-modules-security-fixes**
# **Validates: Requirements 1.3, 4.3**


class SecurityModuleError(SharedModuleError):
    """Base exception for security module errors."""

    pass


class EncryptionError(SecurityModuleError):
    """Base encryption error with context.

    Raised when encryption operations fail.

    Attributes:
        context: Additional context about the error.
    """

    def __init__(
        self,
        message: str,
        context: dict[str, object] | None = None,
    ) -> None:
        """Initialize encryption error.

        Args:
            message: Human-readable error message.
            context: Additional context about the error.
        """
        self.context = context or {}
        super().__init__(message)


class DecryptionError(EncryptionError):
    """Decryption failed.

    Raised when decryption fails due to invalid key, corrupted data,
    or authentication failure.
    """

    pass


class AuthenticationError(DecryptionError):
    """Authentication tag verification failed.

    Raised when the GCM authentication tag doesn't match,
    indicating potential data tampering.
    """

    pass


class PatternValidationError(SecurityModuleError):
    """Invalid regex pattern.

    Raised when pattern validation fails due to dangerous patterns
    or invalid syntax.

    Attributes:
        pattern: The invalid pattern.
        reason: Reason for the validation failure.
    """

    def __init__(self, pattern: str, reason: str) -> None:
        """Initialize pattern validation error.

        Args:
            pattern: The invalid pattern.
            reason: Reason for the validation failure.
        """
        self.pattern = pattern
        self.reason = reason
        super().__init__(f"Invalid pattern '{pattern}': {reason}")
