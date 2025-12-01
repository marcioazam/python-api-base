"""Security type definitions using PEP 593 Annotated types.

**Feature: core-types-split-2025**
"""

from typing import Annotated

from pydantic import Field, StringConstraints

__all__ = [
    "JWTToken",
    "Password",
    "SecurePassword",
]

Password = Annotated[
    str,
    StringConstraints(min_length=8, max_length=128),
    Field(description="Password (8-128 characters)"),
]
"""Password with minimum length requirement."""

SecurePassword = Annotated[
    str,
    StringConstraints(
        min_length=12,
        max_length=128,
        pattern=r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]+$",
    ),
    Field(description="Secure password (12+ chars, mixed case, number, special)"),
]
"""Secure password with complexity requirements."""

JWTToken = Annotated[
    str,
    StringConstraints(
        min_length=20,
        pattern=r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$",
    ),
    Field(description="JWT token (header.payload.signature)"),
]
"""JWT token with basic format validation."""
