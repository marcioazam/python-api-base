"""Base error classes for application layer.

Provides fundamental exception types for error handling.

**Feature: python-api-base-2025-state-of-art**
"""

from application.common.errors.base.application_error import ApplicationError
from application.common.errors.base.handler_not_found import HandlerNotFoundError

__all__ = [
    "ApplicationError",
    "HandlerNotFoundError",
]
