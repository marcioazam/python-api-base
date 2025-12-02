"""Compatibility alias for core.errors.base.application_errors."""

from core.errors.base.application_errors import (
    ApplicationError,
    CommandHandlerError,
    ConcurrencyError,
    HandlerNotFoundError,
    InvalidCommandError,
    InvalidQueryError,
    QueryHandlerError,
    TransactionError,
    UseCaseError,
)

__all__ = [
    "ApplicationError",
    "CommandHandlerError",
    "ConcurrencyError",
    "HandlerNotFoundError",
    "InvalidCommandError",
    "InvalidQueryError",
    "QueryHandlerError",
    "TransactionError",
    "UseCaseError",
]
