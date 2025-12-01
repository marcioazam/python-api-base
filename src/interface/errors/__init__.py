"""Error handling module for interface layer.

**Feature: interface-layer-generics-review**
"""

from interface.errors.exceptions import (
    InterfaceError,
    ValidationError,
    FieldError,
    NotFoundError,
    UnwrapError,
    BuilderValidationError,
    InvalidStatusTransitionError,
    TransformationError,
    ConfigurationError,
)
from interface.errors.messages import (
    ErrorCode,
    ErrorMessage,
)

__all__ = [
    "InterfaceError",
    "ValidationError",
    "FieldError",
    "NotFoundError",
    "UnwrapError",
    "BuilderValidationError",
    "InvalidStatusTransitionError",
    "TransformationError",
    "ConfigurationError",
    "ErrorCode",
    "ErrorMessage",
]
