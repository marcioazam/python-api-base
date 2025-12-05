"""CQRS exceptions module.

Provides custom exceptions for CQRS infrastructure.

**Feature: python-api-base-2025-state-of-art**
"""

from application.common.cqrs.exceptions.exceptions import (
    CQRSError,
    HandlerAlreadyRegisteredError,
    HandlerNotFoundError,
    MiddlewareError,
)

__all__ = [
    "CQRSError",
    "HandlerAlreadyRegisteredError",
    "HandlerNotFoundError",
    "MiddlewareError",
]
