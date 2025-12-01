"""Generic CRUD module for FastAPI applications."""

from .repository import GenericRepository, FilterCondition, FilterOperator, QueryOptions, PaginatedResult, SortCondition
from .service import GenericService, ServiceResult, ValidationRule
from .endpoints import GenericEndpoints, EndpointConfig, EndpointFactory

__all__ = [
    "GenericRepository",
    "FilterCondition",
    "FilterOperator",
    "QueryOptions",
    "PaginatedResult",
    "SortCondition",
    "GenericService",
    "ServiceResult",
    "ValidationRule",
    "GenericEndpoints",
    "EndpointConfig",
    "EndpointFactory",
]
