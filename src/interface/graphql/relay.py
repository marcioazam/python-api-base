"""Relay Connection specification types.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 20.2**
"""

from dataclasses import dataclass


@dataclass
class PageInfo:
    """Relay-style page info."""

    has_next_page: bool
    has_previous_page: bool
    start_cursor: str | None = None
    end_cursor: str | None = None


@dataclass
class Edge[T]:
    """Relay-style edge."""

    node: T
    cursor: str


@dataclass
class Connection[T]:
    """Relay-style connection."""

    edges: list[Edge[T]]
    page_info: PageInfo
    total_count: int | None = None
