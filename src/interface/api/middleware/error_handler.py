"""Global exception handlers for FastAPI."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from my_app.core.exceptions import (
    AppException,
    AuthenticationError,
    RateLimitExceededError,
)
from my_app.application.common.dto import ProblemDetail

logger = logging.getLogger(__name__)


def create_problem_detail(
    request: Request,
    status: int,
    title: str,
    error_code: str,
    detail: str | None = None,
    errors: list[dict] | None = None,
) -> dict[str, Any]:
    """Create RFC 7807 Problem Details response."""
    return ProblemDetail(
        type=f"https://api.example.com/errors/{error_code}",
        title=title,
        status=status,
        detail=detail,
        instance=str(request.url),
        errors=errors,
    ).model_dump()


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle application exceptions."""
    content = create_problem_detail(
        request=request,
        status=exc.status_code,
        title=exc.error_code.replace("_", " ").title(),
        error_code=exc.error_code,
        detail=exc.message,
        errors=exc.details.get("errors") if exc.details else None,
    )

    headers = {}
    if isinstance(exc, AuthenticationError):
        headers["WWW-Authenticate"] = exc.details.get("scheme", "Bearer")
    elif isinstance(exc, RateLimitExceededError):
        headers["Retry-After"] = str(exc.details.get("retry_after", 60))

    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers=headers if headers else None,
    )


async def validation_exception_handler(
    request: Request, exc: PydanticValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "code": error["type"],
        })

    content = create_problem_detail(
        request=request,
        status=422,
        title="Validation Error",
        error_code="VALIDATION_ERROR",
        detail="Request validation failed",
        errors=errors,
    )

    return JSONResponse(status_code=422, content=content)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors without exposing internals."""
    # Log the full error for debugging
    logger.exception(
        "Unhandled exception",
        exc_info=exc,
        extra={"request_url": str(request.url), "method": request.method},
    )

    # Return generic error without internal details
    content = create_problem_detail(
        request=request,
        status=500,
        title="Internal Server Error",
        error_code="INTERNAL_ERROR",
        detail="An unexpected error occurred. Please try again later.",
    )

    return JSONResponse(status_code=500, content=content)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(PydanticValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
