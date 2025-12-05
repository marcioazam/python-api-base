"""Generic API response wrapper DTO.

Provides standard response wrapper with metadata for API communication.

**Feature: application-layer-improvements-2025**
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ApiResponse[T](BaseModel):
    """Generic API response wrapper.

    Wraps any data type with standard response metadata including
    message, status code, timestamp, and request ID for tracing.

    Type Parameters:
        T: The type of data being wrapped in the response.

    Example:
        >>> response = ApiResponse(
        ...     data={"id": "123", "name": "John"},
        ...     message="User retrieved successfully",
        ...     status_code=200,
        ...     request_id="req-456"
        ... )
    """

    data: T
    message: str = Field(default="Success", description="Response message")
    status_code: int = Field(
        default=200, ge=100, le=599, description="HTTP status code"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="Response timestamp in UTC",
    )
    request_id: str | None = Field(default=None, description="Request ID for tracing")

    model_config = {"from_attributes": True}
