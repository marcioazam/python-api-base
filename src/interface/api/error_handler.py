"""RFC 7807/9457 compliant error handling middleware.

Converts exceptions to ProblemDetail responses following the
RFC 7807 Problem Details for HTTP APIs specification.
"""

import logging
import traceback
from datetime import datetime, UTC
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details response.

    Standard format for HTTP API error responses providing
    machine-readable error details.
    """

    type: str = Field(
        default="about:blank",
        description="URI reference identifying the problem type",
    )
    title: str = Field(description="Short, human-readable summary")
    status: int = Field(ge=100, le=599, description="HTTP status code")
    detail: str | None = Field(
        default=None,
        description="Human-readable explanation specific to this occurrence",
    )
    instance: str | None = Field(
        default=None,
        description="URI reference identifying the specific occurrence",
    )
    errors: list[dict[str, Any]] | None = Field(
        default=None,
        description="List of validation errors with field details",
    )
    trace_id: str | None = Field(
        default=None,
        description="Trace ID for debugging",
    )
    timestamp: str | None = Field(
        default=None,
        description="ISO 8601 timestamp",
    )


# Error type URIs
ERROR_TYPES = {
    400: "https://httpstatuses.com/400",
    401: "https://httpstatuses.com/401",
    403: "https://httpstatuses.com/403",
    404: "https://httpstatuses.com/404",
    409: "https://httpstatuses.com/409",
    422: "https://httpstatuses.com/422",
    429: "https://httpstatuses.com/429",
    500: "https://httpstatuses.com/500",
    502: "https://httpstatuses.com/502",
    503: "https://httpstatuses.com/503",
    504: "https://httpstatuses.com/504",
}

# Status code titles
STATUS_TITLES = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    409: "Conflict",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
}


def create_problem_detail(
    status_code: int,
    detail: str | None = None,
    errors: list[dict[str, Any]] | None = None,
    instance: str | None = None,
    trace_id: str | None = None,
    error_type: str | None = None,
    title: str | None = None,
) -> ProblemDetail:
    """Create a ProblemDetail response.

    Args:
        status_code: HTTP status code.
        detail: Human-readable error description.
        errors: List of validation errors.
        instance: URI of the specific occurrence.
        trace_id: Trace ID for debugging.
        error_type: Custom error type URI.
        title: Custom title (defaults to status code title).

    Returns:
        ProblemDetail instance.
    """
    return ProblemDetail(
        type=error_type or ERROR_TYPES.get(status_code, "about:blank"),
        title=title or STATUS_TITLES.get(status_code, "Error"),
        status=status_code,
        detail=detail,
        instance=instance,
        errors=errors,
        trace_id=trace_id or str(uuid4()),
        timestamp=datetime.now(tz=UTC).isoformat(),
    )


def problem_response(
    status_code: int,
    detail: str | None = None,
    errors: list[dict[str, Any]] | None = None,
    instance: str | None = None,
    trace_id: str | None = None,
) -> JSONResponse:
    """Create a JSONResponse with ProblemDetail content.

    Args:
        status_code: HTTP status code.
        detail: Human-readable error description.
        errors: List of validation errors.
        instance: URI of the specific occurrence.
        trace_id: Trace ID for debugging.

    Returns:
        JSONResponse with application/problem+json content type.
    """
    problem = create_problem_detail(
        status_code=status_code,
        detail=detail,
        errors=errors,
        instance=instance,
        trace_id=trace_id,
    )
    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(exclude_none=True),
        media_type="application/problem+json",
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Handle HTTP exceptions and convert to ProblemDetail."""
    trace_id = getattr(request.state, "trace_id", None) or str(uuid4())

    logger.warning(
        "HTTP exception",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
            "trace_id": trace_id,
        },
    )

    return problem_response(
        status_code=exc.status_code,
        detail=str(exc.detail) if exc.detail else None,
        instance=str(request.url),
        trace_id=trace_id,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle validation exceptions and convert to ProblemDetail."""
    trace_id = getattr(request.state, "trace_id", None) or str(uuid4())

    errors = []
    for error in exc.errors():
        loc = ".".join(str(x) for x in error.get("loc", []))
        errors.append({
            "field": loc,
            "message": error.get("msg", "Validation error"),
            "type": error.get("type", "value_error"),
        })

    logger.warning(
        "Validation error",
        extra={
            "errors": errors,
            "path": request.url.path,
            "trace_id": trace_id,
        },
    )

    return problem_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Request validation failed",
        errors=errors,
        instance=str(request.url),
        trace_id=trace_id,
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unhandled exceptions and convert to ProblemDetail."""
    trace_id = getattr(request.state, "trace_id", None) or str(uuid4())

    logger.error(
        "Unhandled exception",
        extra={
            "error": str(exc),
            "error_type": type(exc).__name__,
            "path": request.url.path,
            "trace_id": trace_id,
            "traceback": traceback.format_exc(),
        },
    )

    # Don't expose internal error details in production
    return problem_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred",
        instance=str(request.url),
        trace_id=trace_id,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI app.

    Args:
        app: FastAPI application instance.
    """
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)


# Domain exception mappings
class DomainExceptionMapper:
    """Maps domain exceptions to HTTP status codes."""

    _mappings: dict[type[Exception], int] = {}

    @classmethod
    def register(cls, exception_type: type[Exception], status_code: int) -> None:
        """Register a domain exception mapping."""
        cls._mappings[exception_type] = status_code

    @classmethod
    def get_status_code(cls, exception: Exception) -> int:
        """Get HTTP status code for an exception."""
        for exc_type, code in cls._mappings.items():
            if isinstance(exception, exc_type):
                return code
        return status.HTTP_500_INTERNAL_SERVER_ERROR


# Register common domain exceptions
def setup_domain_exception_mappings() -> None:
    """Set up mappings for common domain exceptions."""
    from src.core.errors.exceptions import (
        NotFoundError,
        ValidationError,
        UnauthorizedError,
        ForbiddenError,
        ConflictError,
    )

    DomainExceptionMapper.register(NotFoundError, status.HTTP_404_NOT_FOUND)
    DomainExceptionMapper.register(ValidationError, status.HTTP_422_UNPROCESSABLE_ENTITY)
    DomainExceptionMapper.register(UnauthorizedError, status.HTTP_401_UNAUTHORIZED)
    DomainExceptionMapper.register(ForbiddenError, status.HTTP_403_FORBIDDEN)
    DomainExceptionMapper.register(ConflictError, status.HTTP_409_CONFLICT)
