"""Generic API Endpoints with auto-generation and OpenAPI schema."""

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field
from sqlmodel import SQLModel

from .repository import FilterCondition, FilterOperator, SortCondition
from .service import GenericService, ServiceResult


class EndpointConfig:
    """Configuration for endpoint generation."""

    def __init__(
        self,
        create: bool = True,
        read: bool = True,
        update: bool = True,
        delete: bool = True,
        list_endpoint: bool = True,
        bulk_create: bool = False,
        bulk_update: bool = False,
        bulk_delete: bool = False,
    ) -> None:
        self.create = create
        self.read = read
        self.update = update
        self.delete = delete
        self.list_endpoint = list_endpoint
        self.bulk_create = bulk_create
        self.bulk_update = bulk_update
        self.bulk_delete = bulk_delete


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(20, ge=1, le=100, description="Items per page")


class FilterParams(BaseModel):
    """Dynamic filter parameters."""

    filters: str | None = Field(None, description='JSON filters: [{"field": "name", "operator": "eq", "value": "test"}]')


class SortParams(BaseModel):
    """Dynamic sort parameters."""

    sort: str | None = Field(None, description="Sort fields: field1:asc,field2:desc")


class GenericEndpoints[T: SQLModel, CreateSchemaType: BaseModel, UpdateSchemaType: BaseModel, ResponseSchemaType: BaseModel]:
    """Generic CRUD endpoints generator."""

    def __init__(
        self,
        service: GenericService[T, CreateSchemaType, UpdateSchemaType, ResponseSchemaType],
        create_schema: type[CreateSchemaType],
        update_schema: type[UpdateSchemaType],
        response_schema: type[ResponseSchemaType],
        prefix: str = "",
        tags: list[str] | None = None,
        config: EndpointConfig | None = None,
    ) -> None:
        self._service = service
        self._create_schema = create_schema
        self._update_schema = update_schema
        self._response_schema = response_schema
        self._prefix = prefix
        self._tags = tags or []
        self._config = config or EndpointConfig()
        self._router = APIRouter(prefix=prefix, tags=self._tags)
        self._setup_endpoints()

    @property
    def router(self) -> APIRouter:
        return self._router

    def _parse_filters(self, filters_str: str | None) -> list[FilterCondition]:
        """Parse filter string to FilterCondition objects."""
        if not filters_str:
            return []
        try:
            filters_data = json.loads(filters_str)
            conditions = []
            for filter_data in filters_data:
                operator = FilterOperator(filter_data.get("operator", "eq"))
                condition = FilterCondition(
                    field=filter_data["field"],
                    operator=operator,
                    value=filter_data["value"],
                    case_sensitive=filter_data.get("case_sensitive", True),
                )
                conditions.append(condition)
            return conditions
        except (json.JSONDecodeError, KeyError, ValueError):
            return []

    def _parse_sorts(self, sort_str: str | None) -> list[SortCondition]:
        """Parse sort string to SortCondition objects."""
        if not sort_str:
            return []
        conditions = []
        for sort_item in sort_str.split(","):
            parts = sort_item.strip().split(":")
            field = parts[0]
            ascending = len(parts) == 1 or parts[1].lower() != "desc"
            conditions.append(SortCondition(field=field, ascending=ascending))
        return conditions

    def _handle_service_result(self, result: ServiceResult) -> Any:
        """Handle service result and convert to HTTP response."""
        if result.success:
            return result.data
        if result.errors:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"message": result.error or "Validation failed", "errors": result.errors},
            )
        status_code = status.HTTP_404_NOT_FOUND if "not found" in (result.error or "").lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=result.error)

    def _setup_endpoints(self) -> None:
        """Setup all CRUD endpoints based on configuration."""
        if self._config.create:
            self._add_create_endpoint()
        if self._config.read:
            self._add_read_endpoint()
        if self._config.list_endpoint:
            self._add_list_endpoint()
        if self._config.update:
            self._add_update_endpoint()
        if self._config.delete:
            self._add_delete_endpoint()
        if self._config.bulk_create:
            self._add_bulk_create_endpoint()

    def _add_create_endpoint(self) -> None:
        @self._router.post(
            "/",
            response_model=self._response_schema,
            status_code=status.HTTP_201_CREATED,
            summary=f"Create {self._response_schema.__name__}",
        )
        async def create_item(item: self._create_schema) -> Any:
            result = await self._service.create(item)
            return self._handle_service_result(result)

    def _add_read_endpoint(self) -> None:
        @self._router.get(
            "/{item_id}",
            response_model=self._response_schema,
            summary=f"Get {self._response_schema.__name__}",
        )
        async def get_item(
            item_id: Any = Path(..., description="Item ID"),
            include_relations: str | None = Query(None, description="Comma-separated relations"),
        ) -> Any:
            relations = include_relations.split(",") if include_relations else None
            result = await self._service.get(item_id, relations)
            return self._handle_service_result(result)

    def _add_list_endpoint(self) -> None:
        @self._router.get(
            "/",
            response_model=dict[str, Any],
            summary=f"List {self._response_schema.__name__}s",
        )
        async def list_items(
            pagination: PaginationParams = Depends(),
            filter_params: FilterParams = Depends(),
            sort_params: SortParams = Depends(),
            include_relations: str | None = Query(None, description="Comma-separated relations"),
        ) -> Any:
            filters = self._parse_filters(filter_params.filters)
            sorts = self._parse_sorts(sort_params.sort)
            relations = include_relations.split(",") if include_relations else None
            result = await self._service.get_paginated(
                page=pagination.page,
                per_page=pagination.per_page,
                filters=filters,
                sorts=sorts,
                include_relations=relations,
            )
            if result.success:
                paginated = result.data
                return {
                    "items": paginated.items,
                    "pagination": {
                        "page": paginated.page,
                        "per_page": paginated.per_page,
                        "total": paginated.total,
                        "has_next": paginated.has_next,
                        "has_prev": paginated.has_prev,
                    },
                }
            return self._handle_service_result(result)

    def _add_update_endpoint(self) -> None:
        @self._router.put(
            "/{item_id}",
            response_model=self._response_schema,
            summary=f"Update {self._response_schema.__name__}",
        )
        async def update_item(item_id: Any = Path(..., description="Item ID"), item: self._update_schema = None) -> Any:
            result = await self._service.update(item_id, item)
            return self._handle_service_result(result)

    def _add_delete_endpoint(self) -> None:
        @self._router.delete(
            "/{item_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary=f"Delete {self._response_schema.__name__}",
        )
        async def delete_item(item_id: Any = Path(..., description="Item ID")) -> None:
            result = await self._service.delete(item_id)
            if not result.success:
                self._handle_service_result(result)

    def _add_bulk_create_endpoint(self) -> None:
        @self._router.post(
            "/bulk",
            response_model=list[self._response_schema],
            status_code=status.HTTP_201_CREATED,
            summary=f"Bulk Create {self._response_schema.__name__}s",
        )
        async def bulk_create_items(items: list[self._create_schema]) -> Any:
            result = await self._service.bulk_create(items)
            return self._handle_service_result(result)


class EndpointFactory:
    """Factory for creating generic endpoints."""

    @staticmethod
    def create_crud_router(
        service: GenericService,
        create_schema: type[BaseModel],
        update_schema: type[BaseModel],
        response_schema: type[BaseModel],
        prefix: str = "",
        tags: list[str] | None = None,
        config: EndpointConfig | None = None,
    ) -> APIRouter:
        """Create a CRUD router for a service."""
        endpoints = GenericEndpoints(
            service=service,
            create_schema=create_schema,
            update_schema=update_schema,
            response_schema=response_schema,
            prefix=prefix,
            tags=tags,
            config=config,
        )
        return endpoints.router


def add_health_check(router: APIRouter) -> None:
    """Add health check endpoint."""

    @router.get("/health", tags=["Health"])
    async def health_check() -> dict[str, str]:
        return {"status": "healthy"}


def add_count_endpoint(router: APIRouter, service: GenericService, path: str = "/count") -> None:
    """Add count endpoint."""

    @router.get(path, response_model=dict[str, int])
    async def count_items(filter_params: FilterParams = Depends()) -> dict[str, int]:
        filters = GenericEndpoints._parse_filters(None, filter_params.filters)
        result = await service.count(filters)
        if result.success:
            return {"count": result.data}
        raise HTTPException(status_code=400, detail=result.error)


def add_exists_endpoint(router: APIRouter, service: GenericService, path: str = "/{item_id}/exists") -> None:
    """Add exists check endpoint."""

    @router.get(path, response_model=dict[str, bool])
    async def item_exists(item_id: Any = Path(...)) -> dict[str, bool]:
        result = await service.exists(item_id)
        if result.success:
            return {"exists": result.data}
        raise HTTPException(status_code=400, detail=result.error)
