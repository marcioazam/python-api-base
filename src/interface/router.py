"""Generic CRUD router factory for FastAPI with PEP 695 generics.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.
Provides automatic generation of REST endpoints with full OpenAPI documentation.

**Feature: architecture-validation-fixes-2025**
**Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.5**
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from collections.abc import Callable, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from application.common.base.dto import ApiResponse, PaginatedResponse


class RouteOperation(Enum):
    """Available CRUD operations for route configuration."""

    LIST = "list"
    GET = "get"
    CREATE = "create"
    UPDATE = "update"
    PATCH = "patch"
    DELETE = "delete"
    BULK_CREATE = "bulk_create"
    BULK_DELETE = "bulk_delete"


@dataclass
class CRUDRouterConfig:
    """Configuration for CRUD router behavior.

    **Feature: architecture-validation-fixes-2025**
    **Validates: Requirements 13.5**
    """

    # Route enablement
    enabled_operations: set[RouteOperation] = field(
        default_factory=lambda: {op for op in RouteOperation}
    )

    # Pagination defaults
    default_page_size: int = 20
    max_page_size: int = 100

    # Response customization
    wrap_responses: bool = True
    include_timestamp: bool = True

    # OpenAPI customization
    operation_id_prefix: str = ""
    deprecated: bool = False


class BulkDeleteRequest(BaseModel):
    """Request model for bulk delete operations."""

    ids: list[str]


class BulkDeleteResponse(BaseModel):
    """Response model for bulk delete operations."""

    deleted_count: int
    failed_ids: list[str]


class GenericCRUDRouter[T, CreateDTO, UpdateDTO, ResponseDTO]:
    """Generic router factory that generates type-safe CRUD endpoints.

    Creates standard REST endpoints for any entity type with full OpenAPI
    documentation and generic response models. All type parameters are
    reflected in the generated OpenAPI specification.

    Type Parameters:
        T: Entity type (used for internal typing).
        CreateDTO: Pydantic model for create requests.
        UpdateDTO: Pydantic model for update requests.
        ResponseDTO: Pydantic model for responses.

    Example:
        >>> router = GenericCRUDRouter[Item, ItemCreate, ItemUpdate, ItemResponse](
        ...     prefix="/items",
        ...     tags=["Items"],
        ...     response_model=ItemResponse,
        ...     create_model=ItemCreate,
        ...     update_model=ItemUpdate,
        ...     use_case_dependency=get_item_use_case,
        ... )
        >>> app.include_router(router.router)

    **Feature: architecture-validation-fixes-2025**
    **Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.5**
    """

    def __init__(
        self,
        *,
        prefix: str,
        tags: list[str],
        response_model: type[ResponseDTO],
        create_model: type[CreateDTO],
        update_model: type[UpdateDTO],
        use_case_dependency: Callable[..., Any],
        config: CRUDRouterConfig | None = None,
        additional_dependencies: Sequence[Callable[..., Any]] | None = None,
    ) -> None:
        """Initialize generic CRUD router factory.

        Args:
            prefix: URL prefix for routes (e.g., "/items").
            tags: OpenAPI tags for documentation.
            response_model: Pydantic model for responses.
            create_model: Pydantic model for create requests.
            update_model: Pydantic model for update requests.
            use_case_dependency: FastAPI dependency that provides use case.
            config: Optional router configuration.
            additional_dependencies: Extra dependencies for all routes.
        """
        self._config = config or CRUDRouterConfig()
        self._additional_deps = list(additional_dependencies or [])
        self.router = APIRouter(prefix=prefix, tags=tags)
        self._response_model = response_model
        self._create_model = create_model
        self._update_model = update_model
        self._use_case_dep = use_case_dependency
        self._setup_routes()

    def _is_enabled(self, operation: RouteOperation) -> bool:
        """Check if an operation is enabled."""
        return operation in self._config.enabled_operations

    def _setup_routes(self) -> None:
        """Set up all CRUD routes based on configuration."""
        if self._is_enabled(RouteOperation.LIST):
            self._setup_list_route()
        if self._is_enabled(RouteOperation.GET):
            self._setup_get_route()
        if self._is_enabled(RouteOperation.CREATE):
            self._setup_create_route()
        if self._is_enabled(RouteOperation.UPDATE):
            self._setup_update_route()
        if self._is_enabled(RouteOperation.PATCH):
            self._setup_patch_route()
        if self._is_enabled(RouteOperation.DELETE):
            self._setup_delete_route()
        if self._is_enabled(RouteOperation.BULK_CREATE):
            self._setup_bulk_create_route()
        if self._is_enabled(RouteOperation.BULK_DELETE):
            self._setup_bulk_delete_route()

    def _setup_list_route(self) -> None:
        """Setup GET / endpoint for listing items with pagination."""
        response_model = self._response_model
        use_case_dep = self._use_case_dep
        config = self._config

        @self.router.get(
            "",
            response_model=PaginatedResponse[response_model],
            summary="List all items",
            deprecated=config.deprecated,
        )
        async def list_items(
            page: int = Query(1, ge=1, description="Page number"),
            size: int = Query(
                config.default_page_size,
                ge=1,
                le=config.max_page_size,
                description="Items per page",
            ),
            sort_by: str | None = Query(None, description="Field to sort by"),
            sort_order: str = Query("asc", pattern="^(asc|desc)$"),
            use_case: Any = Depends(use_case_dep),
        ) -> PaginatedResponse[response_model]:
            return await use_case.list(
                page=page, size=size, sort_by=sort_by, sort_order=sort_order
            )

    def _setup_get_route(self) -> None:
        """Setup GET /{id} endpoint for retrieving single item."""
        response_model = self._response_model
        use_case_dep = self._use_case_dep

        @self.router.get(
            "/{id}",
            response_model=ApiResponse[response_model],
            summary="Get item by ID",
            deprecated=self._config.deprecated,
        )
        async def get_item(
            id: str, use_case: Any = Depends(use_case_dep)
        ) -> ApiResponse[response_model]:
            try:
                return ApiResponse(data=await use_case.get(id))
            except Exception as e:
                if hasattr(e, "status_code") and e.status_code == 404:
                    raise HTTPException(status_code=404, detail=str(e)) from e
                raise

    def _setup_create_route(self) -> None:
        """Setup POST / endpoint for creating items."""
        response_model = self._response_model
        create_model = self._create_model
        use_case_dep = self._use_case_dep

        @self.router.post(
            "",
            response_model=ApiResponse[response_model],
            status_code=status.HTTP_201_CREATED,
            summary="Create new item",
            deprecated=self._config.deprecated,
        )
        async def create_item(
            data: create_model, use_case: Any = Depends(use_case_dep)
        ) -> ApiResponse[response_model]:
            return ApiResponse(data=await use_case.create(data), status_code=201)

    def _setup_update_route(self) -> None:
        """Setup PUT /{id} endpoint for full updates."""
        response_model = self._response_model
        update_model = self._update_model
        use_case_dep = self._use_case_dep

        @self.router.put(
            "/{id}",
            response_model=ApiResponse[response_model],
            summary="Update item (full replacement)",
            deprecated=self._config.deprecated,
        )
        async def update_item(
            id: str, data: update_model, use_case: Any = Depends(use_case_dep)
        ) -> ApiResponse[response_model]:
            try:
                return ApiResponse(data=await use_case.update(id, data))
            except Exception as e:
                if hasattr(e, "status_code") and e.status_code == 404:
                    raise HTTPException(status_code=404, detail=str(e)) from e
                raise

    def _setup_patch_route(self) -> None:
        """Setup PATCH /{id} endpoint for partial updates.

        **Feature: architecture-validation-fixes-2025**
        **Validates: Requirements 13.2**
        """
        response_model = self._response_model
        update_model = self._update_model
        use_case_dep = self._use_case_dep

        @self.router.patch(
            "/{id}",
            response_model=ApiResponse[response_model],
            summary="Update item (partial)",
            deprecated=self._config.deprecated,
        )
        async def patch_item(
            id: str, data: update_model, use_case: Any = Depends(use_case_dep)
        ) -> ApiResponse[response_model]:
            try:
                return ApiResponse(data=await use_case.update(id, data))
            except Exception as e:
                if hasattr(e, "status_code") and e.status_code == 404:
                    raise HTTPException(status_code=404, detail=str(e)) from e
                raise

    def _setup_delete_route(self) -> None:
        """Setup DELETE /{id} endpoint for removing items."""
        use_case_dep = self._use_case_dep

        @self.router.delete(
            "/{id}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary="Delete item",
            deprecated=self._config.deprecated,
        )
        async def delete_item(id: str, use_case: Any = Depends(use_case_dep)) -> None:
            try:
                await use_case.delete(id)
            except Exception as e:
                if hasattr(e, "status_code") and e.status_code == 404:
                    raise HTTPException(status_code=404, detail=str(e)) from e
                raise

    def _setup_bulk_create_route(self) -> None:
        """Setup POST /bulk endpoint for bulk creation."""
        response_model = self._response_model
        create_model = self._create_model
        use_case_dep = self._use_case_dep

        @self.router.post(
            "/bulk",
            response_model=ApiResponse[list[response_model]],
            status_code=status.HTTP_201_CREATED,
            summary="Bulk create items",
            deprecated=self._config.deprecated,
        )
        async def bulk_create_items(
            data: list[create_model], use_case: Any = Depends(use_case_dep)
        ) -> ApiResponse[list[response_model]]:
            return ApiResponse(data=await use_case.create_many(data), status_code=201)

    def _setup_bulk_delete_route(self) -> None:
        """Setup DELETE /bulk endpoint for bulk deletion."""
        use_case_dep = self._use_case_dep

        @self.router.delete(
            "/bulk",
            response_model=BulkDeleteResponse,
            summary="Bulk delete items",
            deprecated=self._config.deprecated,
        )
        async def bulk_delete_items(
            request: BulkDeleteRequest, use_case: Any = Depends(use_case_dep)
        ) -> BulkDeleteResponse:
            deleted_count, failed_ids = 0, []
            for item_id in request.ids:
                try:
                    await use_case.delete(item_id)
                    deleted_count += 1
                except Exception:
                    failed_ids.append(item_id)
            return BulkDeleteResponse(
                deleted_count=deleted_count, failed_ids=failed_ids
            )


# Convenience factory function
def create_crud_router[T, CreateDTO, UpdateDTO, ResponseDTO](
    *,
    prefix: str,
    tags: list[str],
    response_model: type[ResponseDTO],
    create_model: type[CreateDTO],
    update_model: type[UpdateDTO],
    use_case_dependency: Callable[..., Any],
    config: CRUDRouterConfig | None = None,
) -> APIRouter:
    """Factory function to create a CRUD router.

    Returns the underlying APIRouter ready to be included in an app.

    **Feature: architecture-validation-fixes-2025**
    **Validates: Requirements 13.1, 13.2**
    """
    crud_router = GenericCRUDRouter[T, CreateDTO, UpdateDTO, ResponseDTO](
        prefix=prefix,
        tags=tags,
        response_model=response_model,
        create_model=create_model,
        update_model=update_model,
        use_case_dependency=use_case_dependency,
        config=config,
    )
    return crud_router.router
