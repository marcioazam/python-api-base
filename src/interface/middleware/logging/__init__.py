"""Logging and error handling middleware.

**Feature: api-base-improvements**
**Validates: Requirements 9.1, 9.2, 9.3, 9.5**
"""

from interface.middleware.logging.error_handler import (
    app_exception_handler,
    create_problem_detail,
    register_exception_handlers,
)
from interface.middleware.logging.request_logger import (
    RequestLoggerMiddleware,
)

__all__ = [
    "app_exception_handler",
    "create_problem_detail",
    "register_exception_handlers",
    "RequestLoggerMiddleware",
]
