"""String type definitions using PEP 593 Annotated types.

**Feature: core-types-split-2025**
"""

from typing import Annotated

from pydantic import Field, StringConstraints

__all__ = [
    "Email",
    "HttpUrl",
    "ISODateStr",
    "LongStr",
    "MediumStr",
    "NonEmptyStr",
    "PhoneNumber",
    "ShortStr",
    "Slug",
    "TrimmedStr",
    "URLPath",
    "VersionStr",
]

# =============================================================================
# Basic String Types
# =============================================================================

NonEmptyStr = Annotated[
    str,
    StringConstraints(min_length=1, strip_whitespace=True),
    Field(description="Non-empty string (whitespace stripped)"),
]
"""Non-empty string with whitespace stripping."""

TrimmedStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True),
    Field(description="String with whitespace stripped"),
]
"""String with leading/trailing whitespace stripped."""

ShortStr = Annotated[
    str,
    StringConstraints(max_length=100, strip_whitespace=True),
    Field(description="Short string (max 100 chars)"),
]
"""Short string limited to 100 characters."""

MediumStr = Annotated[
    str,
    StringConstraints(max_length=500, strip_whitespace=True),
    Field(description="Medium string (max 500 chars)"),
]
"""Medium string limited to 500 characters."""

LongStr = Annotated[
    str,
    StringConstraints(max_length=5000),
    Field(description="Long string (max 5000 chars)"),
]
"""Long string limited to 5000 characters."""

Slug = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    ),
    Field(description="URL-safe slug (lowercase, hyphens)"),
]
"""URL-safe slug (lowercase letters, numbers, hyphens)."""

# =============================================================================
# Contact Types
# =============================================================================

Email = Annotated[
    str,
    StringConstraints(
        min_length=5,
        max_length=254,
        pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    ),
    Field(description="Email address"),
]
"""Email address with basic validation."""

PhoneNumber = Annotated[
    str,
    StringConstraints(
        min_length=10,
        max_length=20,
        pattern=r"^\+?[0-9\s\-\(\)]+$",
    ),
    Field(description="Phone number (international format supported)"),
]
"""Phone number with international format support."""

# =============================================================================
# URL Types
# =============================================================================

HttpUrl = Annotated[
    str,
    StringConstraints(
        min_length=10,
        max_length=2048,
        pattern=r"^https?://[^\s]+$",
    ),
    Field(description="HTTP/HTTPS URL"),
]
"""HTTP or HTTPS URL."""

URLPath = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=2048,
        pattern=r"^/[a-zA-Z0-9\-._~:/?#\[\]@!$&'()*+,;=%]*$",
    ),
    Field(description="URL path component (e.g., /api/v1/users)"),
]
"""URL path component with validation."""

# =============================================================================
# Technical Types
# =============================================================================

VersionStr = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=20,
        pattern=r"^v?\d+(\.\d+)*(-[a-zA-Z0-9]+)?$",
    ),
    Field(description="Version string (e.g., v1.0.0, 2.1.0-beta)"),
]
"""Semantic version string."""

ISODateStr = Annotated[
    str,
    StringConstraints(
        min_length=10,
        max_length=30,
        pattern=r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?)?$",
    ),
    Field(description="ISO 8601 date/datetime string"),
]
"""ISO 8601 formatted date or datetime string."""
