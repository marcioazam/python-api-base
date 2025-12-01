"""Generic DTOs for API responses.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.
"""

from datetime import datetime, UTC

from pydantic import BaseModel, Field, computed_field


class ApiResponse[T](BaseModel):
    """Generic API response wrapper.

    Wraps any data type with standard response metadata including
    message, status code, timestamp, and request ID for tracing.
    """

    data: T
    message: str = Field(default="Success", description="Response message")
    status_code: int = Field(default=200, ge=100, le=599, description="HTTP status code")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="Response timestamp in UTC",
    )
    request_id: str | None = Field(
        default=None, description="Request ID for tracing"
    )

    model_config = {"from_attributes": True}


class PaginatedResponse[T](BaseModel):
    """Generic paginated response.

    Contains a list of items along with pagination metadata
    including computed fields for total pages and navigation flags.
    """

    items: list[T] = Field(description="List of items for current page")
    total: int = Field(ge=0, description="Total number of items across all pages")
    page: int = Field(ge=1, description="Current page number (1-indexed)")
    size: int = Field(ge=1, le=100, description="Number of items per page")

    @computed_field
    @property
    def pages(self) -> int:
        """Calculate total number of pages."""
        if self.total == 0:
            return 0
        return (self.total + self.size - 1) // self.size

    @computed_field
    @property
    def has_next(self) -> bool:
        """Check if there is a next page."""
        return self.page < self.pages

    @computed_field
    @property
    def has_previous(self) -> bool:
        """Check if there is a previous page."""
        return self.page > 1

    model_config = {"from_attributes": True}


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details response.

    Standard format for HTTP API error responses providing
    machine-readable error details.
    """

    type: str = Field(
        default="about:blank",
        description="URI reference identifying the problem type",
    )
    title: str = Field(description="Short, human-readable summary of the problem")
    status: int = Field(ge=100, le=599, description="HTTP status code")
    detail: str | None = Field(
        default=None, description="Human-readable explanation specific to this occurrence"
    )
    instance: str | None = Field(
        default=None, description="URI reference identifying the specific occurrence"
    )
    errors: list[dict] | None = Field(
        default=None, description="List of validation errors with field details"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "https://api.example.com/errors/VALIDATION_ERROR",
                    "title": "Validation Error",
                    "status": 422,
                    "detail": "Request validation failed",
                    "instance": "/api/v1/items",
                    "errors": [
                        {
                            "field": "price",
                            "message": "Price must be greater than 0",
                            "code": "value_error.number.not_gt",
                        }
                    ],
                }
            ]
        }
    }
