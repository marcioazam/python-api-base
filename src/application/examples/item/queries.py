"""CQRS Queries for ItemExample.

**Feature: application-common-integration**
**Validates: Requirements 2.4, 2.5**
"""

from dataclasses import dataclass

from core.base.cqrs.query import BaseQuery
from application.examples.item.dtos import ItemExampleResponse
from application.common.base.dto import PaginatedResponse


@dataclass(frozen=True, kw_only=True)
class GetItemQuery(BaseQuery[ItemExampleResponse]):
    """Query to get a single ItemExample by ID."""
    
    item_id: str


@dataclass(frozen=True, kw_only=True)
class ListItemsQuery(BaseQuery[PaginatedResponse[ItemExampleResponse]]):
    """Query to list ItemExamples with pagination and filters."""
    
    page: int = 1
    size: int = 20
    category: str | None = None
    status: str | None = None
    sort_by: str = "created_at"
    sort_order: str = "desc"
