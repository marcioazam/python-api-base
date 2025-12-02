"""Unit tests for RFC 7807 Problem Details.

**Feature: enterprise-infrastructure-2025**
**Requirement: R7 - RFC 7807 Problem Details**
"""

import pytest
from http import HTTPStatus

from core.errors.problem_details import (
    ProblemDetail,
    ValidationErrorDetail,
    PROBLEM_JSON_MEDIA_TYPE,
)


class TestProblemDetail:
    """Tests for ProblemDetail model."""

    def test_from_status_with_http_status(self) -> None:
        """Test creating ProblemDetail from HTTPStatus."""
        problem = ProblemDetail.from_status(
            HTTPStatus.NOT_FOUND,
            detail="User not found",
        )

        assert problem.status == 404
        assert problem.title == "Not Found"
        assert problem.detail == "User not found"

    def test_from_status_with_int(self) -> None:
        """Test creating ProblemDetail from int status."""
        problem = ProblemDetail.from_status(
            400,
            detail="Bad request",
        )

        assert problem.status == 400
        assert problem.title == "Bad Request"

    def test_validation_error(self) -> None:
        """Test creating validation error ProblemDetail."""
        errors = [
            ValidationErrorDetail(
                field="email",
                message="Invalid email format",
                code="invalid_format",
            ),
            ValidationErrorDetail(
                field="age",
                message="Must be positive",
                code="invalid_range",
            ),
        ]

        problem = ProblemDetail.validation_error(
            errors=errors,
            instance="/api/v1/users",
            correlation_id="test-123",
        )

        assert problem.status == 422
        assert problem.title == "Validation Error"
        assert len(problem.errors) == 2
        assert problem.correlation_id == "test-123"
        assert problem.instance == "/api/v1/users"

    def test_not_found(self) -> None:
        """Test creating not found ProblemDetail."""
        problem = ProblemDetail.not_found(
            resource="User",
            resource_id="123",
        )

        assert problem.status == 404
        assert "User" in problem.detail
        assert "123" in problem.detail

    def test_unauthorized(self) -> None:
        """Test creating unauthorized ProblemDetail."""
        problem = ProblemDetail.unauthorized()

        assert problem.status == 401
        assert problem.title == "Unauthorized"

    def test_forbidden(self) -> None:
        """Test creating forbidden ProblemDetail."""
        problem = ProblemDetail.forbidden(detail="Admin access required")

        assert problem.status == 403
        assert problem.detail == "Admin access required"

    def test_conflict(self) -> None:
        """Test creating conflict ProblemDetail."""
        problem = ProblemDetail.conflict(detail="Email already exists")

        assert problem.status == 409
        assert problem.detail == "Email already exists"

    def test_internal_error_hides_details(self) -> None:
        """Test internal error doesn't expose sensitive info."""
        problem = ProblemDetail.internal_error(correlation_id="trace-456")

        assert problem.status == 500
        assert "unexpected" in problem.detail.lower()
        assert problem.correlation_id == "trace-456"
        # Should not expose stack traces or internal details
        assert "traceback" not in problem.detail.lower()
        assert "exception" not in problem.detail.lower()

    def test_rate_limited(self) -> None:
        """Test creating rate limited ProblemDetail."""
        problem = ProblemDetail.rate_limited(retry_after=60)

        assert problem.status == 429
        assert problem.retry_after == 60
        assert "60" in problem.detail

    def test_service_unavailable(self) -> None:
        """Test creating service unavailable ProblemDetail."""
        problem = ProblemDetail.service_unavailable(
            service="Redis",
            retry_after=30,
        )

        assert problem.status == 503
        assert "Redis" in problem.detail
        assert problem.retry_after == 30

    def test_json_serialization(self) -> None:
        """Test ProblemDetail JSON serialization."""
        problem = ProblemDetail.validation_error(
            errors=[
                ValidationErrorDetail(
                    field="name",
                    message="Required",
                    code="required",
                )
            ],
            correlation_id="abc-123",
        )

        data = problem.model_dump(mode="json", exclude_none=True)

        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "errors" in data
        assert data["correlation_id"] == "abc-123"

    def test_timestamp_auto_generated(self) -> None:
        """Test timestamp is auto-generated."""
        problem = ProblemDetail.from_status(400)

        assert problem.timestamp is not None


class TestValidationErrorDetail:
    """Tests for ValidationErrorDetail."""

    def test_basic_error(self) -> None:
        """Test basic validation error."""
        error = ValidationErrorDetail(
            field="email",
            message="Invalid format",
        )

        assert error.field == "email"
        assert error.message == "Invalid format"
        assert error.code == "validation_error"

    def test_with_value(self) -> None:
        """Test validation error with value."""
        error = ValidationErrorDetail(
            field="age",
            message="Must be positive",
            code="invalid_range",
            value=-5,
        )

        assert error.value == -5


class TestContentType:
    """Tests for RFC 7807 content type."""

    def test_media_type_constant(self) -> None:
        """Test media type constant."""
        assert PROBLEM_JSON_MEDIA_TYPE == "application/problem+json"
