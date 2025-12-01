"""Centralized error messages with i18n support.

This module provides a unified approach to error message creation with
consistent structure and parameterized templates.

Example:
    >>> error = ErrorMessage.not_found("User", "123")
    >>> assert error.code == ErrorCode.NOT_FOUND
    >>> assert "User" in error.message

**Feature: interface-layer-generics-review**
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """Centralized error codes for all interface operations.

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


@dataclass(frozen=True, slots=True)
class ErrorMessage:
    """Structured error message with code, message, and optional details.

    Args:
        code: Error code from ErrorCode enum
        message: Human-readable error message
        details: Optional additional error context
    """

    code: ErrorCode
    message: str
    details: dict[str, Any] | None = None

    @classmethod
    def not_found(cls, resource: str, id: str) -> ErrorMessage:
        """Create a NOT_FOUND error message.

        Args:
            resource: Type of resource that was not found
            id: Identifier of the resource

        Returns:
            ErrorMessage with NOT_FOUND code
        """
        return cls(
            code=ErrorCode.NOT_FOUND,
            message=f"{resource} with id '{id}' not found",
            details={"resource": resource, "id": id},
        )

    @classmethod
    def validation_error(cls, field: str, reason: str) -> ErrorMessage:
        """Create a VALIDATION_ERROR message.

        Args:
            field: Field that failed validation
            reason: Reason for validation failure

        Returns:
            ErrorMessage with VALIDATION_ERROR code
        """
        return cls(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"Validation failed for field '{field}': {reason}",
            details={"field": field, "reason": reason},
        )

    @classmethod
    def unauthorized(cls, reason: str = "Authentication required") -> ErrorMessage:
        """Create an UNAUTHORIZED error message.

        Args:
            reason: Reason for unauthorized access

        Returns:
            ErrorMessage with UNAUTHORIZED code
        """
        return cls(
            code=ErrorCode.UNAUTHORIZED,
            message=f"Unauthorized: {reason}",
            details={"reason": reason},
        )

    @classmethod
    def forbidden(cls, resource: str, action: str) -> ErrorMessage:
        """Create a FORBIDDEN error message.

        Args:
            resource: Resource being accessed
            action: Action being attempted

        Returns:
            ErrorMessage with FORBIDDEN code
        """
        return cls(
            code=ErrorCode.FORBIDDEN,
            message=f"Forbidden: Cannot {action} {resource}",
            details={"resource": resource, "action": action},
        )

    @classmethod
    def conflict(cls, resource: str, reason: str) -> ErrorMessage:
        """Create a CONFLICT error message.

        Args:
            resource: Resource in conflict
            reason: Reason for conflict

        Returns:
            ErrorMessage with CONFLICT code
        """
        return cls(
            code=ErrorCode.CONFLICT,
            message=f"Conflict with {resource}: {reason}",
            details={"resource": resource, "reason": reason},
        )

    @classmethod
    def internal_error(
        cls, context: str = "An unexpected error occurred"
    ) -> ErrorMessage:
        """Create an INTERNAL_ERROR message.

        Args:
            context: Context about the internal error

        Returns:
            ErrorMessage with INTERNAL_ERROR code
        """
        return cls(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Internal error: {context}",
            details={"context": context},
        )

    @classmethod
    def timeout(cls, operation: str, duration_ms: int) -> ErrorMessage:
        """Create a TIMEOUT error message.

        Args:
            operation: Operation that timed out
            duration_ms: Timeout duration in milliseconds

        Returns:
            ErrorMessage with TIMEOUT code
        """
        return cls(
            code=ErrorCode.TIMEOUT,
            message=f"Operation '{operation}' timed out after {duration_ms}ms",
            details={"operation": operation, "duration_ms": duration_ms},
        )

    @classmethod
    def rate_limited(cls, limit: int, window_seconds: int) -> ErrorMessage:
        """Create a RATE_LIMITED error message.

        Args:
            limit: Rate limit threshold
            window_seconds: Rate limit window in seconds

        Returns:
            ErrorMessage with RATE_LIMITED code
        """
        return cls(
            code=ErrorCode.RATE_LIMITED,
            message=f"Rate limit exceeded: {limit} requests per {window_seconds} seconds",
            details={"limit": limit, "window_seconds": window_seconds},
        )

    @classmethod
    def bad_request(cls, reason: str) -> ErrorMessage:
        """Create a BAD_REQUEST error message.

        Args:
            reason: Reason for bad request

        Returns:
            ErrorMessage with BAD_REQUEST code
        """
        return cls(
            code=ErrorCode.BAD_REQUEST,
            message=f"Bad request: {reason}",
            details={"reason": reason},
        )

    @classmethod
    def service_unavailable(
        cls, service: str, retry_after_seconds: int | None = None
    ) -> ErrorMessage:
        """Create a SERVICE_UNAVAILABLE error message.

        Args:
            service: Name of unavailable service
            retry_after_seconds: Optional retry delay

        Returns:
            ErrorMessage with SERVICE_UNAVAILABLE code
        """
        message = f"Service '{service}' is unavailable"
        details: dict[str, Any] = {"service": service}

        if retry_after_seconds is not None:
            message += f", retry after {retry_after_seconds} seconds"
            details["retry_after_seconds"] = retry_after_seconds

        return cls(code=ErrorCode.SERVICE_UNAVAILABLE, message=message, details=details)

    @classmethod
    def method_not_found(cls, method: str) -> ErrorMessage:
        """Create a METHOD_NOT_FOUND error message.

        Args:
            method: Method name that was not found

        Returns:
            ErrorMessage with METHOD_NOT_FOUND code
        """
        return cls(
            code=ErrorCode.METHOD_NOT_FOUND,
            message=f"Method '{method}' not found",
            details={"method": method},
        )

    @classmethod
    def invalid_params(cls, params: str, reason: str) -> ErrorMessage:
        """Create an INVALID_PARAMS error message.

        Args:
            params: Parameter name(s) that are invalid
            reason: Reason for invalidity

        Returns:
            ErrorMessage with INVALID_PARAMS code
        """
        return cls(
            code=ErrorCode.INVALID_PARAMS,
            message=f"Invalid parameters '{params}': {reason}",
            details={"params": params, "reason": reason},
        )

    @classmethod
    def from_key(cls, key: str, **kwargs: Any) -> ErrorMessage:
        """Create error message from key with fallback.

        Args:
            key: Error message key
            **kwargs: Template parameters

        Returns:
            ErrorMessage with appropriate code or generic error
        """
        return cls(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Unknown error key: {key}",
            details={"key": key, "params": kwargs},
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        result: dict[str, Any] = {
            "code": self.code.value,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result

    def to_problem_details(
        self, type_uri: str = "about:blank", instance: str | None = None
    ) -> dict[str, Any]:
        """Convert to RFC 7807 Problem Details format.

        Args:
            type_uri: URI reference for error type
            instance: URI reference for specific occurrence

        Returns:
            Problem Details dictionary
        """
        status_map = {
            ErrorCode.NOT_FOUND: 404,
            ErrorCode.VALIDATION_ERROR: 400,
            ErrorCode.UNAUTHORIZED: 401,
            ErrorCode.FORBIDDEN: 403,
            ErrorCode.CONFLICT: 409,
            ErrorCode.INTERNAL_ERROR: 500,
            ErrorCode.TIMEOUT: 504,
            ErrorCode.RATE_LIMITED: 429,
            ErrorCode.BAD_REQUEST: 400,
            ErrorCode.SERVICE_UNAVAILABLE: 503,
        }

        result: dict[str, Any] = {
            "type": type_uri,
            "title": self.code.value.replace("_", " ").title(),
            "status": status_map.get(self.code, 500),
            "detail": self.message,
        }

        if instance:
            result["instance"] = instance

        if self.details:
            result["extensions"] = self.details

        return result
