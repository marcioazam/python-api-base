"""HTTP status codes and error code constants.

**Feature: 2025-generics-clean-code-review**
**Feature: interface-layer-generics-review**
**Validates: Requirements 10.2**
"""

from enum import IntEnum, Enum


class HttpStatus(IntEnum):
    """HTTP status codes as enum for type safety."""

    # 2xx Success
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204

    # 3xx Redirection
    MOVED_PERMANENTLY = 301
    FOUND = 302
    NOT_MODIFIED = 304
    TEMPORARY_REDIRECT = 307
    PERMANENT_REDIRECT = 308

    # 4xx Client Errors
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    GONE = 410
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429

    # 5xx Server Errors
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504


class ErrorCode(str, Enum):
    """Centralized error codes for all operations.

    All error codes use SCREAMING_SNAKE_CASE convention.
    """

    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    CONFLICT = "CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    BAD_REQUEST = "BAD_REQUEST"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    NETWORK_ERROR = "NETWORK_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    PRECONDITION_FAILED = "PRECONDITION_FAILED"
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
    METHOD_NOT_FOUND = "METHOD_NOT_FOUND"
    INVALID_PARAMS = "INVALID_PARAMS"
    PARSE_ERROR = "PARSE_ERROR"


# Alias for backward compatibility
ErrorCodes = ErrorCode


class ErrorMessages:
    """Centralized error messages for consistency."""

    # Authentication errors
    INVALID_CREDENTIALS = "Invalid credentials provided"
    TOKEN_EXPIRED = "Authentication token has expired"
    TOKEN_INVALID = "Invalid authentication token"
    UNAUTHORIZED = "Authentication required"

    # Authorization errors
    FORBIDDEN = "Access denied"
    INSUFFICIENT_PERMISSIONS = "Insufficient permissions for this operation"

    # Validation errors
    VALIDATION_FAILED = "Validation failed"
    REQUIRED_FIELD = "This field is required"
    INVALID_FORMAT = "Invalid format"
    INVALID_VALUE = "Invalid value"

    # Resource errors
    NOT_FOUND = "Resource not found"
    ALREADY_EXISTS = "Resource already exists"
    CONFLICT = "Resource conflict"

    # Rate limiting
    RATE_LIMIT_EXCEEDED = "Rate limit exceeded"

    # Server errors
    INTERNAL_ERROR = "An internal error occurred"
    SERVICE_UNAVAILABLE = "Service temporarily unavailable"
    TIMEOUT = "Operation timed out"

    @classmethod
    def not_found(cls, resource: str, id: str) -> str:
        """Create a not found message."""
        return f"{resource} with id '{id}' not found"

    @classmethod
    def validation_error(cls, field: str, reason: str) -> str:
        """Create a validation error message."""
        return f"Validation failed for field '{field}': {reason}"

    @classmethod
    def already_exists(cls, resource: str, field: str, value: str) -> str:
        """Create an already exists message."""
        return f"{resource} with {field} '{value}' already exists"
