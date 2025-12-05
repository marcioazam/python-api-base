"""Item example handlers (Command/Query handlers).

**Feature: example-system-demo**
"""

from application.examples.item.handlers.handlers import (
    CreateItemHandler,
    DeleteItemHandler,
    GetItemByIdHandler,
    ListItemsHandler,
    UpdateItemHandler,
)

__all__ = [
    "CreateItemHandler",
    "UpdateItemHandler",
    "DeleteItemHandler",
    "GetItemByIdHandler",
    "ListItemsHandler",
]
