"""Generic CRUD router for FastAPI."""

from typing import Any
from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from my_api.shared.dto import ApiResponse, PaginatedResponse


class BulkDeleteRequest(BaseModel):
    """Request model for bulk delete operations."""

    ids: list[str]


class BulkDeleteResponse(BaseModel):
    """Response model for bulk delete operations."""

    deleted_count: int
    failed_ids: list[str]


class GenericCRUDRouter[T, CreateDTO, UpdateDTO, ResponseDTO]:
    """Generic router that generates CRUD endpoints.

    Creates standard REST endpoints for any entity type with
    proper OpenAPI documentation and response models.
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
    ) -> None:
        """Initialize generic CRUD router.

        Args:
            prefix: URL prefix for routes (e.g., "/items").
            tags: OpenAPI tags for documentation.
            response_model: Pydantic model for responses.
            create_model: Pydantic model for create requests.
            update_model: Pydantic model for update requests.
            use_case_dependency: FastAPI dependency that provides use case.
        """
        self.router = APIRouter(prefix=prefix, tags=tags)
        self._setup_routes(
            response_model, create_model, update_model, use_case_dependency
        )

    def _setup_routes(
        self,
        response_model: type[ResponseDTO],
        create_model: type[CreateDTO],
        update_model: type[UpdateDTO],
        use_case_dep: Callable[..., Any],
    ) -> None:
        """Set up all CRUD routes."""
        self._setup_list_route(response_model, use_case_dep)
        self._setup_get_route(response_model, use_case_dep)
        self._setup_create_route(response_model, create_model, use_case_dep)
        self._setup_update_route(response_model, update_model, use_case_dep)
        self._setup_delete_route(use_case_dep)
        self._setup_bulk_routes(response_model, create_model, use_case_dep)

    def _setup_list_route(self, response_model: type, use_case_dep: Callable) -> None:
        @self.router.get("", response_model=PaginatedResponse[response_model], summary="List all items")
        async def list_items(
            page: int = 1, size: int = 20, sort_by: str | None = None,
            sort_order: str = "asc", use_case: Any = Depends(use_case_dep),
        ) -> PaginatedResponse[response_model]:
            return await use_case.list(page=page, size=size, sort_by=sort_by, sort_order=sort_order)

    def _setup_get_route(self, response_model: type, use_case_dep: Callable) -> None:
        @self.router.get("/{id}", response_model=ApiResponse[response_model], summary="Get item by ID")
        async def get_item(id: str, use_case: Any = Depends(use_case_dep)) -> ApiResponse[response_model]:
            try:
                return ApiResponse(data=await use_case.get(id))
            except Exception as e:
                if hasattr(e, "status_code") and e.status_code == 404:
                    raise HTTPException(status_code=404, detail=str(e)) from e
                raise

    def _setup_create_route(self, response_model: type, create_model: type, use_case_dep: Callable) -> None:
        @self.router.post("", response_model=ApiResponse[response_model], status_code=status.HTTP_201_CREATED, summary="Create new item")
        async def create_item(data: create_model, use_case: Any = Depends(use_case_dep)) -> ApiResponse[response_model]:
            return ApiResponse(data=await use_case.create(data), status_code=201)

    def _setup_update_route(self, response_model: type, update_model: type, use_case_dep: Callable) -> None:
        @self.router.put("/{id}", response_model=ApiResponse[response_model], summary="Update item")
        async def update_item(id: str, data: update_model, use_case: Any = Depends(use_case_dep)) -> ApiResponse[response_model]:
            try:
                return ApiResponse(data=await use_case.update(id, data))
            except Exception as e:
                if hasattr(e, "status_code") and e.status_code == 404:
                    raise HTTPException(status_code=404, detail=str(e)) from e
                raise

    def _setup_delete_route(self, use_case_dep: Callable) -> None:
        @self.router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete item")
        async def delete_item(id: str, use_case: Any = Depends(use_case_dep)) -> None:
            try:
                await use_case.delete(id)
            except Exception as e:
                if hasattr(e, "status_code") and e.status_code == 404:
                    raise HTTPException(status_code=404, detail=str(e)) from e
                raise

    def _setup_bulk_routes(self, response_model: type, create_model: type, use_case_dep: Callable) -> None:
        @self.router.post("/bulk", response_model=ApiResponse[list[response_model]], status_code=status.HTTP_201_CREATED, summary="Bulk create items")
        async def bulk_create_items(data: list[create_model], use_case: Any = Depends(use_case_dep)) -> ApiResponse[list[response_model]]:
            return ApiResponse(data=await use_case.create_many(data), status_code=201)

        @self.router.delete("/bulk", response_model=BulkDeleteResponse, summary="Bulk delete items")
        async def bulk_delete_items(request: BulkDeleteRequest, use_case: Any = Depends(use_case_dep)) -> BulkDeleteResponse:
            deleted_count, failed_ids = 0, []
            for item_id in request.ids:
                try:
                    await use_case.delete(item_id)
                    deleted_count += 1
                except Exception:
                    failed_ids.append(item_id)
            return BulkDeleteResponse(deleted_count=deleted_count, failed_ids=failed_ids)
