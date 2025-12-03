"""Application layer for ItemExample.

**Feature: application-common-integration**
"""

from application.examples.item.dtos import (
    ItemExampleCreate,
    ItemExampleUpdate,
    ItemExampleResponse,
    ItemExampleListResponse,
)
from application.examples.item.mapper import ItemExampleMapper
from application.examples.item.use_case import ItemExampleUseCase
from application.examples.item.commands import (
    CreateItemCommand,
    UpdateItemCommand,
    DeleteItemCommand,
)
from application.examples.item.queries import (
    GetItemQuery,
    ListItemsQuery,
)
from application.examples.item.handlers import (
    CreateItemCommandHandler,
    UpdateItemCommandHandler,
    DeleteItemCommandHandler,
    GetItemQueryHandler,
    ListItemsQueryHandler,
)

__all__ = [
    # DTOs
    "ItemExampleCreate",
    "ItemExampleUpdate",
    "ItemExampleResponse",
    "ItemExampleListResponse",
    # Mapper
    "ItemExampleMapper",
    # Use Case (legacy)
    "ItemExampleUseCase",
    # Commands
    "CreateItemCommand",
    "UpdateItemCommand",
    "DeleteItemCommand",
    # Queries
    "GetItemQuery",
    "ListItemsQuery",
    # Handlers
    "CreateItemCommandHandler",
    "UpdateItemCommandHandler",
    "DeleteItemCommandHandler",
    "GetItemQueryHandler",
    "ListItemsQueryHandler",
]
