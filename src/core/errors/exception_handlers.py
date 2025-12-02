"""Compatibility alias for core.errors.http.exception_handlers."""

from core.errors.http.exception_handlers import (
    setup_exception_handlers,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)

__all__ = [
    "setup_exception_handlers",
    "http_exception_handler",
    "validation_exception_handler",
    "generic_exception_handler",
]
