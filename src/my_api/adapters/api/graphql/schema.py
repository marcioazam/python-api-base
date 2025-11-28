"""GraphQL schema configuration and router creation.

This module provides utilities for creating GraphQL schemas and
integrating them with FastAPI using Strawberry.

**Feature: api-architecture-analysis, Task 3.1: GraphQL Support with Strawberry**
**Validates: Requirements 4.5**
"""

from typing import Any

import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.schema.config import StrawberryConfig


def create_graphql_router(
    query: type,
    mutation: type | None = None,
    subscription: type | None = None,
    context_getter: Any | None = None,
    prefix: str = "/graphql",
) -> GraphQLRouter:
    """Create a GraphQL router for FastAPI integration.

    Creates a Strawberry GraphQL schema and wraps it in a FastAPI-compatible
    router that can be mounted on the application.

    Args:
        query: The root Query type class decorated with @strawberry.type.
        mutation: Optional root Mutation type class.
        subscription: Optional root Subscription type class.
        context_getter: Optional async function to provide request context.
        prefix: URL prefix for the GraphQL endpoint.

    Returns:
        A GraphQLRouter that can be included in a FastAPI app.

    Example:
        @strawberry.type
        class Query:
            @strawberry.field
            def hello(self) -> str:
                return "Hello, World!"

        router = create_graphql_router(Query)
        app.include_router(router, prefix="/graphql")
    """
    schema = strawberry.Schema(
        query=query,
        mutation=mutation,
        subscription=subscription,
        config=StrawberryConfig(auto_camel_case=True),
    )

    return GraphQLRouter(
        schema,
        context_getter=context_getter,
        path=prefix,
    )


@strawberry.type
class EmptyMutation:
    """Placeholder mutation type when no mutations are defined.

    GraphQL requires at least one field in each root type.
    Use this as a placeholder when your API has no mutations.
    """

    @strawberry.field
    def placeholder(self) -> str:
        """Placeholder field - no mutations available."""
        return "No mutations available"


@strawberry.type
class EmptySubscription:
    """Placeholder subscription type when no subscriptions are defined.

    GraphQL requires at least one field in each root type.
    Use this as a placeholder when your API has no subscriptions.
    """

    @strawberry.subscription
    async def placeholder(self) -> str:  # type: ignore[misc]
        """Placeholder subscription - no subscriptions available."""
        yield "No subscriptions available"
