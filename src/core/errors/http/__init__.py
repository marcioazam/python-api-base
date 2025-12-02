"""HTTP/API error handling.

- Problem Details: RFC 7807 compliant responses
- Exception Handlers: FastAPI exception handlers
- Constants: HTTP status codes and error codes
"""

from core.errors.http.problem_details import (
    ProblemDetail,
    ValidationErrorDetail,
    PROBLEM_JSON_MEDIA_TYPE,
)
from core.errors.http.exception_handlers import (
    setup_exception_handlers,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from core.errors.http.constants import (
    HttpStatus,
    ErrorCode,
    ErrorCodes,
    ErrorMessages,
)

__all__ = [
    # Problem Details
    "ProblemDetail",
    "ValidationErrorDetail",
    "PROBLEM_JSON_MEDIA_TYPE",
    # Exception Handlers
    "setup_exception_handlers",
    "http_exception_handler",
    "validation_exception_handler",
    "generic_exception_handler",
    # Constants
    "HttpStatus",
    "ErrorCode",
    "ErrorCodes",
    "ErrorMessages",
]
