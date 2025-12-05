"""JSON type aliases using PEP 695 type statement.

**Feature: core-types-split-2025**

Note: Forward references are intentional for types defined in other modules.
"""
# ruff: noqa: F821

__all__ = [
    "FilterDict",
    "Headers",
    "JSONArray",
    "JSONObject",
    "JSONPrimitive",
    "JSONValue",
    "QueryParams",
    "SortOrder",
]

# =============================================================================
# JSON Type Aliases
# =============================================================================

type JSONPrimitive = str | int | float | bool | None
"""Type alias for JSON primitive values."""

type JSONValue = JSONPrimitive | list["JSONValue"] | dict[str, "JSONValue"]
"""Type alias for any JSON value."""

type JSONObject = dict[str, JSONValue]
"""Type alias for JSON object."""

type JSONArray = list[JSONValue]
"""Type alias for JSON array."""

# =============================================================================
# Filter and Query Type Aliases
# =============================================================================

type FilterDict = dict[str, "Any"]
"""Type alias for filter dictionary used in repository queries."""

type SortOrder = "Literal['asc', 'desc']"
"""Type alias for sort order in queries."""

type QueryParams = dict[str, str | int | float | bool | None]
"""Type alias for URL query parameters."""

type Headers = dict[str, str]
"""Type alias for HTTP headers."""
