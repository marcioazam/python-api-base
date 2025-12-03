"""FastAPI exception handlers for RFC 7807 Problem Details.

**Feature: enterprise-infrastructure-2025**
**Requirement: R7 - RFC 7807 Problem Details**
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.errors.http.problem_details import (
    ProblemDetail,
    ValidationErrorDetail,
    PROBLEM_JSON_MEDIA_TYPE,
)

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


def _get_correlation_id(request: Request) -> str | None:
    """Extract correlation ID from request.

    **Requirement: R7.5 - Include correlation ID**
    """
    # Check header first
    correlation_id = request.headers.get("X-Correlation-ID")
    if correlation_id:
        return correlation_id

    # Check state (set by middleware)
    if hasattr(request.state, "correlation_id"):
        return request.state.correlation_id

    return None


def _create_problem_response(
    problem: ProblemDetail,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Create JSONResponse with RFC 7807 content type.

    **Requirement: R7.4 - Content-Type header**
    """
    response_headers = {"Content-Type": PROBLEM_JSON_MEDIA_TYPE}
    if headers:
        response_headers.update(headers)

    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(mode="json", exclude_none=True),
        headers=response_headers,
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Handle HTTP exceptions with RFC 7807 format.

    Args:
        request: FastAPI request
        exc: HTTP exception

    Returns:
        RFC 7807 formatted response
    """
    correlation_id = _get_correlation_id(request)

    problem = ProblemDetail.from_status(
        status=exc.status_code,
        detail=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
        instance=str(request.url.path),
        correlation_id=correlation_id,
    )

    logger.warning(
        "HTTP exception",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
            "correlation_id": correlation_id,
        },
    )

    headers = {}
    if exc.headers:
        headers.update(exc.headers)

    return _create_problem_response(problem, headers)


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle validation errors with RFC 7807 format.

    **Requirement: R7.2 - Multiple validation errors**
    **Requirement: R8.4 - 422 status with RFC 7807**

    Args:
        request: FastAPI request
        exc: Validation error

    Returns:
        RFC 7807 formatted response with errors array
    """
    correlation_id = _get_correlation_id(request)

    errors = []
    for error in exc.errors():
        # Build field path from loc
        loc = error.get("loc", [])
        # Skip 'body' prefix if present
        if loc and loc[0] in ("body", "query", "path", "header"):
            loc = loc[1:]
        field_path = ".".join(str(part) for part in loc)

        errors.append(
            ValidationErrorDetail(
                field=field_path or "unknown",
                message=error.get("msg", "Invalid value"),
                code=error.get("type", "validation_error"),
            )
        )

    problem = ProblemDetail.validation_error(
        errors=errors,
        instance=str(request.url.path),
        correlation_id=correlation_id,
    )

    logger.info(
        "Validation error",
        extra={
            "path": request.url.path,
            "error_count": len(errors),
            "correlation_id": correlation_id,
        },
    )

    return _create_problem_response(problem)


async def pydantic_exception_handler(
    request: Request,
    exc: PydanticValidationError,
) -> JSONResponse:
    """Handle Pydantic validation errors with RFC 7807 format.

    **Requirement: R8.1 - Pydantic models with custom validators**

    Args:
        request: FastAPI request
        exc: Pydantic validation error

    Returns:
        RFC 7807 formatted response
    """
    correlation_id = _get_correlation_id(request)

    errors = []
    for error in exc.errors():
        loc = error.get("loc", [])
        field_path = ".".join(str(part) for part in loc)

        errors.append(
            ValidationErrorDetail(
                field=field_path or "unknown",
                message=error.get("msg", "Invalid value"),
                code=error.get("type", "validation_error"),
            )
        )

    problem = ProblemDetail.validation_error(
        errors=errors,
        instance=str(request.url.path),
        correlation_id=correlation_id,
    )

    return _create_problem_response(problem)


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle uncaught exceptions with RFC 7807 format.

    **Requirement: R7.3 - No sensitive information exposed**

    Args:
        request: FastAPI request
        exc: Uncaught exception

    Returns:
        Safe RFC 7807 formatted response
    """
    correlation_id = _get_correlation_id(request)

    # Log full exception details
    logger.exception(
        "Unhandled exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "correlation_id": correlation_id,
            "exception_type": type(exc).__name__,
        },
    )

    # Return safe response without sensitive details
    problem = ProblemDetail.internal_error(
        correlation_id=correlation_id,
        instance=str(request.url.path),
    )

    return _create_problem_response(problem)


def setup_exception_handlers(app: "FastAPI") -> None:
    """Register all RFC 7807 exception handlers.

    Args:
        app: FastAPI application
    """
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(PydanticValidationError, pydantic_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("RFC 7807 exception handlers registered")
