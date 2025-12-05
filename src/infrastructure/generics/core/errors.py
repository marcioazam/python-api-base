"""Centralized error messages and typed error classes.

**Feature: infrastructure-generics-review-2025**
**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

Provides:
- ErrorMessages: Centralized error message constants
- Typed error class hierarchy for infrastructure errors
"""

from typing import Final


class ErrorMessages:
    """Centralized error message constants organized by domain.

    All error messages are defined as Final[str] constants for type safety
    and consistency across the infrastructure layer.
    """

    # =========================================================================
    # Authentication Errors (AUTH_*)
    # =========================================================================
    AUTH_TOKEN_EXPIRED: Final[str] = "Token has expired"  # noqa: S105
    AUTH_TOKEN_INVALID: Final[str] = "Invalid token"  # noqa: S105
    AUTH_TOKEN_REVOKED: Final[str] = "Token has been revoked"  # noqa: S105
    AUTH_TOKEN_MALFORMED: Final[str] = "Token is malformed"  # noqa: S105
    AUTH_ALGORITHM_MISMATCH: Final[str] = (
        "Algorithm mismatch: expected {expected}, got {received}"
    )
    AUTH_KEY_INVALID: Final[str] = "Invalid key format"
    AUTH_KEY_MISSING: Final[str] = "{algorithm} requires {key_type}"
    AUTH_SIGNATURE_INVALID: Final[str] = "Token signature verification failed"
    AUTH_CLAIMS_MISSING: Final[str] = "Required claim missing: {claim}"
    AUTH_ISSUER_INVALID: Final[str] = "Invalid token issuer"
    AUTH_AUDIENCE_INVALID: Final[str] = "Invalid token audience"

    # =========================================================================
    # Cache Errors (CACHE_*)
    # =========================================================================
    CACHE_KEY_NOT_FOUND: Final[str] = "Cache key not found: {key}"
    CACHE_SERIALIZATION_FAILED: Final[str] = "Failed to serialize cache value: {error}"
    CACHE_DESERIALIZATION_FAILED: Final[str] = (
        "Failed to deserialize cache value: {error}"
    )
    CACHE_CONNECTION_FAILED: Final[str] = "Cache connection failed: {error}"
    CACHE_OPERATION_TIMEOUT: Final[str] = "Cache operation timed out after {timeout}s"
    CACHE_TAG_NOT_FOUND: Final[str] = "Cache tag not found: {tag}"

    # =========================================================================
    # Connection Pool Errors (POOL_*)
    # =========================================================================
    POOL_EXHAUSTED: Final[str] = "Connection pool exhausted"
    POOL_ACQUIRE_TIMEOUT: Final[str] = "Acquire timeout after {timeout}s"
    POOL_CONNECTION_ERROR: Final[str] = "Connection error: {message}"
    POOL_CLOSED: Final[str] = "Pool is closed"
    POOL_INVALID_STATE: Final[str] = (
        "Invalid pool state transition: {from_state} -> {to_state}"
    )
    POOL_HEALTH_CHECK_FAILED: Final[str] = (
        "Health check failed for connection {conn_id}"
    )

    # =========================================================================
    # Validation Errors (VALIDATION_*)
    # =========================================================================
    VALIDATION_EMPTY_VALUE: Final[str] = "{field} cannot be empty or whitespace"
    VALIDATION_INVALID_FORMAT: Final[str] = "Invalid format for {field}: {reason}"
    VALIDATION_OUT_OF_RANGE: Final[str] = "{field} must be between {min} and {max}"
    VALIDATION_REQUIRED: Final[str] = "{field} is required"
    VALIDATION_TYPE_MISMATCH: Final[str] = "{field} must be of type {expected_type}"
    VALIDATION_PATTERN_MISMATCH: Final[str] = (
        "{field} does not match pattern: {pattern}"
    )

    # =========================================================================
    # Security Errors (SECURITY_*)
    # =========================================================================
    SECURITY_UNAUTHORIZED: Final[str] = "Unauthorized access"
    SECURITY_FORBIDDEN: Final[str] = "Access forbidden"
    SECURITY_RATE_LIMITED: Final[str] = (
        "Rate limit exceeded, retry after {retry_after}s"
    )
    SECURITY_ENCRYPTION_FAILED: Final[str] = "Encryption failed: {error}"
    SECURITY_DECRYPTION_FAILED: Final[str] = "Decryption failed: {error}"
    SECURITY_POLICY_DENIED: Final[str] = "Policy denied access to {resource}"

    # =========================================================================
    # Messaging Errors (MSG_*)
    # =========================================================================
    MSG_PUBLISH_FAILED: Final[str] = "Failed to publish message to {topic}: {error}"
    MSG_SUBSCRIBE_FAILED: Final[str] = "Failed to subscribe to {topic}: {error}"
    MSG_HANDLER_ERROR: Final[str] = "Message handler error: {error}"
    MSG_DEAD_LETTER: Final[str] = (
        "Message moved to dead letter queue after {retries} retries"
    )
    MSG_BROKER_UNAVAILABLE: Final[str] = "Message broker unavailable: {error}"

    # =========================================================================
    # Database Errors (DB_*)
    # =========================================================================
    DB_CONNECTION_FAILED: Final[str] = "Database connection failed: {error}"
    DB_QUERY_FAILED: Final[str] = "Query execution failed: {error}"
    DB_TRANSACTION_FAILED: Final[str] = "Transaction failed: {error}"
    DB_ENTITY_NOT_FOUND: Final[str] = "{entity} with id {id} not found"
    DB_DUPLICATE_KEY: Final[str] = "Duplicate key violation for {entity}"
    DB_CONSTRAINT_VIOLATION: Final[str] = "Constraint violation: {constraint}"

    # =========================================================================
    # Task Errors (TASK_*)
    # =========================================================================
    TASK_EXECUTION_FAILED: Final[str] = "Task execution failed: {error}"
    TASK_TIMEOUT: Final[str] = "Task timed out after {timeout}s"
    TASK_CANCELLED: Final[str] = "Task was cancelled"
    TASK_RETRY_EXHAUSTED: Final[str] = "Task retry exhausted after {retries} attempts"
    TASK_QUEUE_FULL: Final[str] = "Task queue is full"

    @classmethod
    def format(cls, message: str, **kwargs: str | int | float) -> str:
        """Format an error message with parameters.

        Args:
            message: The message template.
            **kwargs: Parameters to substitute.

        Returns:
            Formatted message string.
        """
        return message.format(**kwargs)


class InfrastructureError(Exception):
    """Base class for all infrastructure errors.

    Attributes:
        message: Human-readable error message.
        error_code: Machine-readable error code.
        details: Additional error details.
    """

    def __init__(
        self,
        message: str,
        error_code: str = "INFRASTRUCTURE_ERROR",
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


class AuthenticationError(InfrastructureError):
    """Authentication-related errors."""

    def __init__(
        self,
        message: str = ErrorMessages.AUTH_TOKEN_INVALID,
        error_code: str = "AUTH_ERROR",
        details: dict | None = None,
    ) -> None:
        super().__init__(message, error_code, details)


class CacheError(InfrastructureError):
    """Cache-related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "CACHE_ERROR",
        details: dict | None = None,
    ) -> None:
        super().__init__(message, error_code, details)


class PoolError(InfrastructureError):
    """Connection pool errors."""

    def __init__(
        self,
        message: str = ErrorMessages.POOL_EXHAUSTED,
        error_code: str = "POOL_ERROR",
        details: dict | None = None,
    ) -> None:
        super().__init__(message, error_code, details)


class ValidationError(InfrastructureError):
    """Input validation errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "VALIDATION_ERROR",
        field: str | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(message, error_code, details)
        self.field = field


class SecurityError(InfrastructureError):
    """Security-related errors."""

    def __init__(
        self,
        message: str = ErrorMessages.SECURITY_UNAUTHORIZED,
        error_code: str = "SECURITY_ERROR",
        details: dict | None = None,
    ) -> None:
        super().__init__(message, error_code, details)


class MessagingError(InfrastructureError):
    """Messaging-related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "MESSAGING_ERROR",
        details: dict | None = None,
    ) -> None:
        super().__init__(message, error_code, details)
