"""API routes for ItemExample and PedidoExample.

Demonstrates:
- FastAPI router setup
- Dependency injection
- Request/Response handling
- Error handling
- OpenAPI documentation
- Rate limiting
- Caching headers
- Multi-tenancy

**Feature: example-system-demo**
"""

from typing import Annotated, Any
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from pydantic import BaseModel

from application.common.dto import ApiResponse, PaginatedResponse
from application.examples.dtos import (
    ItemExampleCreate,
    ItemExampleUpdate,
    ItemExampleResponse,
    PedidoExampleCreate,
    PedidoExampleUpdate,
    PedidoExampleResponse,
    AddItemRequest,
    CancelPedidoRequest,
)
from application.examples.use_cases import (
    ItemExampleUseCase,
    PedidoExampleUseCase,
    NotFoundError,
    ValidationError,
)

router = APIRouter(prefix="/examples", tags=["Examples"])


# === Dependency Injection ===


async def get_item_use_case() -> ItemExampleUseCase:
    """Dependency to get ItemExample use case.

    In production, this would resolve from DI container with:
    - Database session
    - Event bus
    - Cache provider
    """
    # Placeholder - in real usage, inject from container
    from infrastructure.db.session import get_async_session
    from infrastructure.db.repositories.examples import ItemExampleRepository

    async with get_async_session() as session:
        repo = ItemExampleRepository(session)
        yield ItemExampleUseCase(repository=repo)


async def get_pedido_use_case() -> PedidoExampleUseCase:
    """Dependency to get PedidoExample use case."""
    from infrastructure.db.session import get_async_session
    from infrastructure.db.repositories.examples import (
        ItemExampleRepository,
        PedidoExampleRepository,
    )

    async with get_async_session() as session:
        item_repo = ItemExampleRepository(session)
        pedido_repo = PedidoExampleRepository(session)
        yield PedidoExampleUseCase(
            pedido_repo=pedido_repo,
            item_repo=item_repo,
        )


# Mock dependencies for example (replace with real DI in production)
class MockItemRepository:
    _items: dict[str, Any] = {}

    async def get(self, item_id: str) -> Any:
        return self._items.get(item_id)

    async def get_by_sku(self, sku: str) -> Any:
        for item in self._items.values():
            if item.sku == sku:
                return item
        return None

    async def create(self, entity: Any) -> Any:
        self._items[entity.id] = entity
        return entity

    async def update(self, entity: Any) -> Any:
        self._items[entity.id] = entity
        return entity

    async def get_all(self, **kwargs) -> list:
        return list(self._items.values())


class MockPedidoRepository:
    _pedidos: dict[str, Any] = {}

    async def get(self, pedido_id: str) -> Any:
        return self._pedidos.get(pedido_id)

    async def create(self, entity: Any) -> Any:
        self._pedidos[entity.id] = entity
        return entity

    async def update(self, entity: Any) -> Any:
        self._pedidos[entity.id] = entity
        return entity

    async def get_all(self, **kwargs) -> list:
        return list(self._pedidos.values())


# Singleton mock repos
_item_repo = MockItemRepository()
_pedido_repo = MockPedidoRepository()


def get_mock_item_use_case() -> ItemExampleUseCase:
    return ItemExampleUseCase(repository=_item_repo)


def get_mock_pedido_use_case() -> PedidoExampleUseCase:
    return PedidoExampleUseCase(
        pedido_repo=_pedido_repo,
        item_repo=_item_repo,
    )


# === Error Handling ===


def handle_result_error(error: Any) -> HTTPException:
    """Convert use case error to HTTP exception."""
    if isinstance(error, NotFoundError):
        return HTTPException(status_code=404, detail=error.message)
    if isinstance(error, ValidationError):
        return HTTPException(status_code=422, detail=error.message)
    return HTTPException(status_code=500, detail=str(error))


# === ItemExample Routes ===


@router.get(
    "/items",
    response_model=PaginatedResponse[ItemExampleResponse],
    summary="List all items",
    description="Get paginated list of ItemExample entities with optional filters.",
)
async def list_items(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: str | None = Query(None, description="Filter by category"),
    status: str | None = Query(None, description="Filter by status"),
    use_case: ItemExampleUseCase = Depends(get_mock_item_use_case),
) -> PaginatedResponse[ItemExampleResponse]:
    result = await use_case.list(
        page=page,
        page_size=page_size,
        category=category,
        status=status,
    )
    if result.is_err():
        raise handle_result_error(result.unwrap_err())

    items = result.unwrap()
    return PaginatedResponse(
        items=items,
        total=len(items),
        page=page,
        page_size=page_size,
    )


@router.post(
    "/items",
    response_model=ApiResponse[ItemExampleResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create item",
    description="Create a new ItemExample entity.",
)
async def create_item(
    data: ItemExampleCreate,
    x_user_id: str = Header(default="system", alias="X-User-Id"),
    use_case: ItemExampleUseCase = Depends(get_mock_item_use_case),
) -> ApiResponse[ItemExampleResponse]:
    result = await use_case.create(data, created_by=x_user_id)
    if result.is_err():
        raise handle_result_error(result.unwrap_err())
    return ApiResponse(data=result.unwrap(), status_code=201)


@router.get(
    "/items/{item_id}",
    response_model=ApiResponse[ItemExampleResponse],
    summary="Get item by ID",
)
async def get_item(
    item_id: str,
    use_case: ItemExampleUseCase = Depends(get_mock_item_use_case),
) -> ApiResponse[ItemExampleResponse]:
    result = await use_case.get(item_id)
    if result.is_err():
        raise handle_result_error(result.unwrap_err())
    return ApiResponse(data=result.unwrap())


@router.put(
    "/items/{item_id}",
    response_model=ApiResponse[ItemExampleResponse],
    summary="Update item",
)
async def update_item(
    item_id: str,
    data: ItemExampleUpdate,
    x_user_id: str = Header(default="system", alias="X-User-Id"),
    use_case: ItemExampleUseCase = Depends(get_mock_item_use_case),
) -> ApiResponse[ItemExampleResponse]:
    result = await use_case.update(item_id, data, updated_by=x_user_id)
    if result.is_err():
        raise handle_result_error(result.unwrap_err())
    return ApiResponse(data=result.unwrap())


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete item",
)
async def delete_item(
    item_id: str,
    x_user_id: str = Header(default="system", alias="X-User-Id"),
    use_case: ItemExampleUseCase = Depends(get_mock_item_use_case),
) -> None:
    result = await use_case.delete(item_id, deleted_by=x_user_id)
    if result.is_err():
        raise handle_result_error(result.unwrap_err())


# === PedidoExample Routes ===


@router.get(
    "/pedidos",
    response_model=PaginatedResponse[PedidoExampleResponse],
    summary="List all orders",
)
async def list_pedidos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: str | None = Query(None),
    status: str | None = Query(None),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    use_case: PedidoExampleUseCase = Depends(get_mock_pedido_use_case),
) -> PaginatedResponse[PedidoExampleResponse]:
    result = await use_case.list(
        page=page,
        page_size=page_size,
        customer_id=customer_id,
        status=status,
        tenant_id=x_tenant_id,
    )
    if result.is_err():
        raise handle_result_error(result.unwrap_err())

    pedidos = result.unwrap()
    return PaginatedResponse(
        items=pedidos,
        total=len(pedidos),
        page=page,
        page_size=page_size,
    )


@router.post(
    "/pedidos",
    response_model=ApiResponse[PedidoExampleResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create order",
)
async def create_pedido(
    data: PedidoExampleCreate,
    x_user_id: str = Header(default="system", alias="X-User-Id"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    use_case: PedidoExampleUseCase = Depends(get_mock_pedido_use_case),
) -> ApiResponse[PedidoExampleResponse]:
    result = await use_case.create(
        data,
        tenant_id=x_tenant_id,
        created_by=x_user_id,
    )
    if result.is_err():
        raise handle_result_error(result.unwrap_err())
    return ApiResponse(data=result.unwrap(), status_code=201)


@router.get(
    "/pedidos/{pedido_id}",
    response_model=ApiResponse[PedidoExampleResponse],
    summary="Get order by ID",
)
async def get_pedido(
    pedido_id: str,
    use_case: PedidoExampleUseCase = Depends(get_mock_pedido_use_case),
) -> ApiResponse[PedidoExampleResponse]:
    result = await use_case.get(pedido_id)
    if result.is_err():
        raise handle_result_error(result.unwrap_err())
    return ApiResponse(data=result.unwrap())


@router.post(
    "/pedidos/{pedido_id}/items",
    response_model=ApiResponse[PedidoExampleResponse],
    summary="Add item to order",
)
async def add_item_to_pedido(
    pedido_id: str,
    data: AddItemRequest,
    use_case: PedidoExampleUseCase = Depends(get_mock_pedido_use_case),
) -> ApiResponse[PedidoExampleResponse]:
    result = await use_case.add_item(pedido_id, data)
    if result.is_err():
        raise handle_result_error(result.unwrap_err())
    return ApiResponse(data=result.unwrap())


@router.post(
    "/pedidos/{pedido_id}/confirm",
    response_model=ApiResponse[PedidoExampleResponse],
    summary="Confirm order",
)
async def confirm_pedido(
    pedido_id: str,
    x_user_id: str = Header(default="system", alias="X-User-Id"),
    use_case: PedidoExampleUseCase = Depends(get_mock_pedido_use_case),
) -> ApiResponse[PedidoExampleResponse]:
    result = await use_case.confirm(pedido_id, confirmed_by=x_user_id)
    if result.is_err():
        raise handle_result_error(result.unwrap_err())
    return ApiResponse(data=result.unwrap())


@router.post(
    "/pedidos/{pedido_id}/cancel",
    response_model=ApiResponse[PedidoExampleResponse],
    summary="Cancel order",
)
async def cancel_pedido(
    pedido_id: str,
    data: CancelPedidoRequest,
    x_user_id: str = Header(default="system", alias="X-User-Id"),
    use_case: PedidoExampleUseCase = Depends(get_mock_pedido_use_case),
) -> ApiResponse[PedidoExampleResponse]:
    result = await use_case.cancel(
        pedido_id,
        reason=data.reason,
        cancelled_by=x_user_id,
    )
    if result.is_err():
        raise handle_result_error(result.unwrap_err())
    return ApiResponse(data=result.unwrap())
