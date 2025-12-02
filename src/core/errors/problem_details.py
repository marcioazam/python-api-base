"""Compatibility alias for core.errors.http.problem_details."""

from core.errors.http.problem_details import (
    ProblemDetail,
    ValidationErrorDetail,
    PROBLEM_JSON_MEDIA_TYPE,
)

__all__ = [
    "ProblemDetail",
    "ValidationErrorDetail",
    "PROBLEM_JSON_MEDIA_TYPE",
]
