"""GraphQL core setup.

Contains schema definition and router setup.

**Feature: interface-restructuring-2025**
"""

from interface.graphql.core.router import graphql_router
from interface.graphql.core.schema import schema

__all__ = [
    "graphql_router",
    "schema",
]
