"""RFC 7807 Problem Details response DTO.

Standard format for HTTP API error responses providing machine-readable error details.

**Feature: application-layer-improvements-2025**
"""

from pydantic import BaseModel, Field


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details response.

    Standard format for HTTP API error responses providing
    machine-readable error details according to RFC 7807.

    Reference: https://tools.ietf.org/html/rfc7807

    Example:
        >>> error = ProblemDetail(
        ...     type="https://api.example.com/errors/VALIDATION_ERROR",
        ...     title="Validation Error",
        ...     status=422,
        ...     detail="Request validation failed",
        ...     instance="/api/v1/items",
        ...     errors=[
        ...         {
        ...             "field": "price",
        ...             "message": "Price must be greater than 0",
        ...             "code": "value_error.number.not_gt",
        ...         }
        ...     ]
        ... )
    """

    type: str = Field(
        default="about:blank",
        description="URI reference identifying the problem type",
    )
    title: str = Field(description="Short, human-readable summary of the problem")
    status: int = Field(ge=100, le=599, description="HTTP status code")
    detail: str | None = Field(
        default=None,
        description="Human-readable explanation specific to this occurrence",
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
