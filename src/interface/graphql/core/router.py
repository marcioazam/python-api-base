"""GraphQL Router integration with FastAPI.

Provides the GraphQL endpoint using Strawberry.

**Feature: interface-modules-workflow-analysis**
**Validates: Requirements 3.1, 3.2, 3.3**
"""

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.fastapi import GraphQLRouter

from infrastructure.db.repositories.examples import (
    ItemExampleRepository,
    PedidoExampleRepository,
)
from infrastructure.db.session import get_async_session
from interface.graphql.schema import schema


async def get_context(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Build GraphQL context with repositories.

    **Feature: interface-modules-workflow-analysis**
    **Validates: Requirements 3.1**
    """
    return {
        "request": request,
        "item_repository": ItemExampleRepository(session),
        "pedido_repository": PedidoExampleRepository(session),
    }


graphql_router = GraphQLRouter(
    schema,
    context_getter=get_context,
    path="/graphql",
)

router = APIRouter(tags=["GraphQL"])
router.include_router(graphql_router, prefix="")
