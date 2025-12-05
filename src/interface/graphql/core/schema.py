"""GraphQL Schema for Examples using Strawberry.

Provides GraphQL queries and mutations for ItemExample and PedidoExample.

**Feature: interface-modules-workflow-analysis**
**Validates: Requirements 3.1, 3.2, 3.3**
**Refactored: Split into types/, queries.py, mutations.py, mappers.py**
"""

import strawberry

from interface.graphql.mutations import Mutation
from interface.graphql.queries import Query

schema = strawberry.Schema(query=Query, mutation=Mutation)

# Re-export for backward compatibility
__all__ = ["Mutation", "Query", "schema"]
