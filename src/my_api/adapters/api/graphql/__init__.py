"""GraphQL adapter module with Strawberry integration.

This module provides generic GraphQL types and utilities for building
type-safe GraphQL APIs with Strawberry.

**Feature: api-architecture-analysis, Task 3.1: GraphQL Support with Strawberry**
**Validates: Requirements 4.5**
"""

from my_api.adapters.api.graphql.types import (
    Connection,
    Edge,
    PageInfo,
    connection_from_list,
)
from my_api.adapters.api.graphql.schema import create_graphql_router

__all__ = [
    "Connection",
    "Edge",
    "PageInfo",
    "connection_from_list",
    "create_graphql_router",
]
