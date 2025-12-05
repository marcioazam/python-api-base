"""CQRS Query infrastructure.

Provides query base class and query bus for read operations.

**Feature: python-api-base-2025-state-of-art**
"""

from application.common.cqrs.queries.query_bus import Query, QueryBus, QueryHandler

__all__ = [
    "Query",
    "QueryBus",
    "QueryHandler",
]
