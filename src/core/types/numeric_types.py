"""Numeric type definitions using PEP 593 Annotated types.

**Feature: core-types-split-2025**
"""

from typing import Annotated

from pydantic import Field

__all__ = [
    "NonNegativeFloat",
    "NonNegativeInt",
    "PageNumber",
    "PageSize",
    "Percentage",
    "PositiveFloat",
    "PositiveInt",
]

# =============================================================================
# Numeric Types
# =============================================================================

PositiveInt = Annotated[
    int,
    Field(gt=0, description="Positive integer (> 0)"),
]
"""Positive integer greater than zero."""

NonNegativeInt = Annotated[
    int,
    Field(ge=0, description="Non-negative integer (>= 0)"),
]
"""Non-negative integer (zero or positive)."""

PositiveFloat = Annotated[
    float,
    Field(gt=0, description="Positive float (> 0)"),
]
"""Positive float greater than zero."""

NonNegativeFloat = Annotated[
    float,
    Field(ge=0, description="Non-negative float (>= 0)"),
]
"""Non-negative float (zero or positive)."""

Percentage = Annotated[
    float,
    Field(ge=0, le=100, description="Percentage value (0-100)"),
]
"""Percentage value between 0 and 100."""

# =============================================================================
# Pagination Types
# =============================================================================

PageNumber = Annotated[
    int,
    Field(ge=1, le=10000, description="Page number (1-indexed)"),
]
"""Page number for pagination (1-indexed, max 10000)."""

PageSize = Annotated[
    int,
    Field(ge=1, le=100, description="Items per page (1-100)"),
]
"""Page size for pagination (1-100 items)."""
