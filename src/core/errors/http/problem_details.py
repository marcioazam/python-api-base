"""RFC 7807 Problem Details for HTTP APIs.

Provides standardized error responses following RFC 7807.

**Feature: enterprise-infrastructure-2025**
**Requirement: R7 - RFC 7807 Problem Details**
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any
from http import HTTPStatus

from pydantic import BaseModel, Field, ConfigDict


class ValidationErrorDetail(BaseModel):
    """Detail for a single validation error.

    **Requirement: R7.2 - Multiple validation errors**
    """

    model_config = ConfigDict(frozen=True)

    field: str = Field(..., description="Field path that caused the error")
    message: str = Field(..., description="Human-readable error message")
    code: str = Field(default="validation_error", description="Error code")
    value: Any = Field(default=None, description="Invalid value (if safe to expose)")


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details response.

    Standard format for HTTP API error responses.

    **Feature: enterprise-infrastructure-2025**
    **Requirement: R7.1 - Problem Details with required fields**

    Attributes:
        type: URI reference identifying the problem type
        title: Short human-readable summary
        status: HTTP status code
        detail: Human-readable explanation
        instance: URI reference identifying the specific occurrence
        errors: List of validation errors (for 422 responses)
        correlation_id: Request correlation ID for tracing
        timestamp: When the error occurred
        extensions: Additional problem-specific data
    """

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "type": "https://api.example.com/problems/validation-error",
                "title": "Validation Error",
                "status": 422,
                "detail": "One or more fields failed validation",
                "instance": "/api/v1/users",
                "errors": [
                    {
                        "field": "email",
                        "message": "Invalid email format",
                        "code": "invalid_format",
                    }
                ],
                "correlation_id": "abc-123-def-456",
            }
        },
    )

    type: str = Field(
        default="about:blank",
        description="URI reference identifying the problem type",
    )
    title: str = Field(
        ...,
        description="Short, human-readable summary of the problem",
    )
    status: int = Field(
        ...,
        ge=100,
        le=599,
        description="HTTP status code",
    )
    detail: str | None = Field(
        default=None,
        description="Human-readable explanation specific to this occurrence",
    )
    instance: str | None = Field(
        default=None,
        description="URI reference identifying the specific occurrence",
    )

    # Extended fields
    errors: list[ValidationErrorDetail] | None = Field(
        default=None,
        description="List of validation errors",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Request correlation ID for tracing",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the error occurred",
    )

    @classmethod
    def from_status(
        cls,
        status: int | HTTPStatus,
        detail: str | None = None,
        **kwargs: Any,
    ) -> ProblemDetail:
        """Create ProblemDetail from HTTP status.

        Args:
            status: HTTP status code or HTTPStatus enum
            detail: Optional detail message
            **kwargs: Additional fields

        Returns:
            ProblemDetail instance
        """
        if isinstance(status, HTTPStatus):
            status_code = status.value
            title = status.phrase
        else:
            status_code = status
            try:
                title = HTTPStatus(status).phrase
            except ValueError:
                title = "Error"

        return cls(
            status=status_code,
            title=title,
            detail=detail,
            **kwargs,
        )

    @classmethod
    def validation_error(
        cls,
        errors: list[ValidationErrorDetail],
        detail: str = "One or more fields failed validation",
        instance: str | None = None,
        correlation_id: str | None = None,
    ) -> ProblemDetail:
        """Create validation error ProblemDetail.

        **Requirement: R8.4 - 422 status with RFC 7807**

        Args:
            errors: List of validation errors
            detail: Error detail message
            instance: Request path
            correlation_id: Correlation ID

        Returns:
            ProblemDetail for validation error
        """
        return cls(
            type="https://tools.ietf.org/html/rfc7807#section-3.1",
            title="Validation Error",
            status=422,
            detail=detail,
            instance=instance,
            errors=errors,
            correlation_id=correlation_id,
        )

    @classmethod
    def not_found(
        cls,
        resource: str,
        resource_id: str | None = None,
        instance: str | None = None,
        correlation_id: str | None = None,
    ) -> ProblemDetail:
        """Create not found ProblemDetail.

        Args:
            resource: Resource type (e.g., "User", "Order")
            resource_id: Resource identifier
            instance: Request path
            correlation_id: Correlation ID

        Returns:
            ProblemDetail for not found error
        """
        detail = f"{resource} not found"
        if resource_id:
            detail = f"{resource} with ID '{resource_id}' not found"

        return cls(
            type="https://tools.ietf.org/html/rfc7231#section-6.5.4",
            title="Not Found",
            status=404,
            detail=detail,
            instance=instance,
            correlation_id=correlation_id,
        )

    @classmethod
    def unauthorized(
        cls,
        detail: str = "Authentication required",
        instance: str | None = None,
        correlation_id: str | None = None,
    ) -> ProblemDetail:
        """Create unauthorized ProblemDetail.

        Args:
            detail: Error detail
            instance: Request path
            correlation_id: Correlation ID

        Returns:
            ProblemDetail for unauthorized error
        """
        return cls(
            type="https://tools.ietf.org/html/rfc7235#section-3.1",
            title="Unauthorized",
            status=401,
            detail=detail,
            instance=instance,
            correlation_id=correlation_id,
        )

    @classmethod
    def forbidden(
        cls,
        detail: str = "Access denied",
        instance: str | None = None,
        correlation_id: str | None = None,
    ) -> ProblemDetail:
        """Create forbidden ProblemDetail.

        Args:
            detail: Error detail
            instance: Request path
            correlation_id: Correlation ID

        Returns:
            ProblemDetail for forbidden error
        """
        return cls(
            type="https://tools.ietf.org/html/rfc7231#section-6.5.3",
            title="Forbidden",
            status=403,
            detail=detail,
            instance=instance,
            correlation_id=correlation_id,
        )

    @classmethod
    def conflict(
        cls,
        detail: str,
        instance: str | None = None,
        correlation_id: str | None = None,
    ) -> ProblemDetail:
        """Create conflict ProblemDetail.

        Args:
            detail: Conflict description
            instance: Request path
            correlation_id: Correlation ID

        Returns:
            ProblemDetail for conflict error
        """
        return cls(
            type="https://tools.ietf.org/html/rfc7231#section-6.5.8",
            title="Conflict",
            status=409,
            detail=detail,
            instance=instance,
            correlation_id=correlation_id,
        )

    @classmethod
    def internal_error(
        cls,
        correlation_id: str | None = None,
        instance: str | None = None,
    ) -> ProblemDetail:
        """Create internal server error ProblemDetail.

        **Requirement: R7.3 - No sensitive information**

        Args:
            correlation_id: Correlation ID for tracing
            instance: Request path

        Returns:
            ProblemDetail for internal error (safe for clients)
        """
        return cls(
            type="https://tools.ietf.org/html/rfc7231#section-6.6.1",
            title="Internal Server Error",
            status=500,
            detail="An unexpected error occurred. Please try again later.",
            instance=instance,
            correlation_id=correlation_id,
        )

    @classmethod
    def rate_limited(
        cls,
        retry_after: int | None = None,
        instance: str | None = None,
        correlation_id: str | None = None,
    ) -> ProblemDetail:
        """Create rate limited ProblemDetail.

        Args:
            retry_after: Seconds until retry is allowed
            instance: Request path
            correlation_id: Correlation ID

        Returns:
            ProblemDetail for rate limit error
        """
        detail = "Rate limit exceeded"
        if retry_after:
            detail = f"Rate limit exceeded. Retry after {retry_after} seconds."

        return cls(
            type="https://tools.ietf.org/html/rfc6585#section-4",
            title="Too Many Requests",
            status=429,
            detail=detail,
            instance=instance,
            correlation_id=correlation_id,
            retry_after=retry_after,
        )

    @classmethod
    def service_unavailable(
        cls,
        service: str | None = None,
        retry_after: int | None = None,
        instance: str | None = None,
        correlation_id: str | None = None,
    ) -> ProblemDetail:
        """Create service unavailable ProblemDetail.

        Args:
            service: Name of unavailable service
            retry_after: Seconds until retry
            instance: Request path
            correlation_id: Correlation ID

        Returns:
            ProblemDetail for service unavailable
        """
        detail = "Service temporarily unavailable"
        if service:
            detail = f"Service '{service}' is temporarily unavailable"

        return cls(
            type="https://tools.ietf.org/html/rfc7231#section-6.6.4",
            title="Service Unavailable",
            status=503,
            detail=detail,
            instance=instance,
            correlation_id=correlation_id,
            retry_after=retry_after,
        )


# Content type for RFC 7807 responses
PROBLEM_JSON_MEDIA_TYPE = "application/problem+json"
