"""GraphQL support module.

Organized into subpackages by responsibility:
- core/: Schema and router setup
- queries/: Query definitions
- mutations/: Mutation definitions
- resolvers/: Resolver functions and data loaders
- mappers/: DTO mappers
- relay/: Relay cursor-based pagination
- types/: GraphQL type definitions

**Feature: python-api-base-2025-generics-audit**
**Feature: interface-modules-workflow-analysis**
**Validates: Requirements 20.1-20.5, 3.1, 3.2, 3.3**
"""

from interface.graphql.mappers import map_user_to_graphql
from interface.graphql.relay import RelayConnection
from interface.graphql.resolvers import DataLoaderService

# Import router and schema for integration
try:
    from interface.graphql.core import graphql_router, schema as graphql_schema

    HAS_STRAWBERRY = True
except ImportError:
    graphql_router = None
    graphql_schema = None
    HAS_STRAWBERRY = False

__all__ = [
    "HAS_STRAWBERRY",
    # Core
    "graphql_router",
    "graphql_schema",
    # Resolvers
    "DataLoaderService",
    # Mappers
    "map_user_to_graphql",
    # Relay
    "RelayConnection",
]
