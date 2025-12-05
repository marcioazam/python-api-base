"""API v2 routes for ItemExample and PedidoExample.

Demonstrates versioned API with deprecation headers.

**Feature: interface-modules-workflow-analysis**
**Validates: Requirements 1.1, 1.2, 1.3**
"""

from typing import Any

from fastapi import Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.common.dto import ApiResponse, PaginatedResponse
from application.examples import (
    ItemExampleCreate,
    ItemExampleResponse,
    ItemExampleUseCase,
    NotFoundError,
    PedidoExampleResponse,
    PedidoExampleUseCase,
    ValidationError,
)
from infrastructure.db.repositories.examples import (
    ItemExampleRepository,
    PedidoExampleRepository,
)
from infrastructure.db.session import get_async_session
from infrastructure.kafka import EventPublisher, create_event_publisher
from interface.versioning import (
    ApiVersion,
    VersionedRouter,
)

# Create versioned router for v2
v2_version = ApiVersion[int](version=2, deprecated=False)
versioned = VersionedRouter[int](
    version=v2_version,
    prefix="/examples",
    tags=["Examples v2"],
)

router = versioned.router


async def get_item_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ItemExampleRepository:
    """Get ItemExampleRepository with injected database session."""
    return ItemExampleRepository(session)


async def get_pedido_repository(
    session: AsyncSession = Depends(get_async_session),
) -> PedidoExampleRepository:
    """Get PedidoExampleRepository with injected database session."""
    return PedidoExampleRepository(session)


def get_event_publisher(request: Request) -> EventPublisher:
    """Get EventPublisher based on Kafka availability."""
    kafka_producer = getattr(request.app.state, "kafka_producer", None)
    return create_event_publisher(kafka_producer)


async def get_item_use_case(
    repo: ItemExampleRepository = Depends(get_item_repository),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> ItemExampleUseCase:
    """Get ItemExampleUseCase with real repository and event publisher."""
    return ItemExampleUseCase(repository=repo, kafka_publisher=event_publisher)


async def get_pedido_use_case(
    item_repo: ItemExampleRepository = Depends(get_item_repository),
    pedido_repo: PedidoExampleRepository = Depends(get_pedido_repository),
) -> PedidoExampleUseCase:
    """Get PedidoExampleUseCase with real repositories."""
    return PedidoExampleUseCase(
        pedido_repo=pedido_repo,
        item_repo=item_repo,
    )


def handle_result_error(error: Any) -> HTTPException:
    """Convert use case error to HTTP exception."""
    if isinstance(error, NotFoundError):
        return HTTPException(status_code=404, detail=error.message)
    if isinstance(error, ValidationError):
        return HTTPException(status_code=422, detail=error.message)
    return HTTPException(status_code=500, detail=str(error))


# === ItemExample v2 Routes ===


@router.get(
    "/items",
    response_model=PaginatedResponse[ItemExampleResponse],
    summary="List all items (v2)",
    description="Get paginated list of ItemExample entities with enhanced filtering.",
)
async def list_items_v2(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: str | None = Query(None, description="Filter by category"),
    status: str | None = Query(None, description="Filter by status"),
    use_case: ItemExampleUseCase = Depends(get_item_use_case),
) -> PaginatedResponse[ItemExampleResponse]:
    """List items with v2 enhanced features.

    **Feature: interface-modules-workflow-analysis**
    **Validates: Requirements 1.1**
    """
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
        size=page_size,
    )


@router.get(
    "/items/{item_id}",
    response_model=ApiResponse[ItemExampleResponse],
    summary="Get item by ID (v2)",
)
async def get_item_v2(
    item_id: str,
    use_case: ItemExampleUseCase = Depends(get_item_use_case),
) -> ApiResponse[ItemExampleResponse]:
    """Get single item with v2 response format.

    **Feature: interface-modules-workflow-analysis**
    **Validates: Requirements 1.1**
    """
    result = await use_case.get(item_id)
    if result.is_err():
        raise handle_result_error(result.unwrap_err())
    return ApiResponse(data=result.unwrap())


@router.post(
    "/items",
    response_model=ApiResponse[ItemExampleResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create item (v2)",
)
async def create_item_v2(
    data: ItemExampleCreate,
    use_case: ItemExampleUseCase = Depends(get_item_use_case),
) -> ApiResponse[ItemExampleResponse]:
    """Create item with v2 validation.

    **Feature: interface-modules-workflow-analysis**
    **Validates: Requirements 1.1**
    """
    result = await use_case.create(data, created_by="v2-api")
    if result.is_err():
        raise handle_result_error(result.unwrap_err())
    return ApiResponse(data=result.unwrap(), status_code=201)


# === PedidoExample v2 Routes ===


@router.get(
    "/pedidos",
    response_model=PaginatedResponse[PedidoExampleResponse],
    summary="List all orders (v2)",
)
async def list_pedidos_v2(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: str | None = Query(None),
    status: str | None = Query(None),
    use_case: PedidoExampleUseCase = Depends(get_pedido_use_case),
) -> PaginatedResponse[PedidoExampleResponse]:
    """List pedidos with v2 features.

    **Feature: interface-modules-workflow-analysis**
    **Validates: Requirements 1.1**
    """
    result = await use_case.list(
        page=page,
        page_size=page_size,
        customer_id=customer_id,
        status=status,
    )
    if result.is_err():
        raise handle_result_error(result.unwrap_err())

    pedidos = result.unwrap()
    return PaginatedResponse(
        items=pedidos,
        total=len(pedidos),
        page=page,
        size=page_size,
    )


@router.get(
    "/pedidos/{pedido_id}",
    response_model=ApiResponse[PedidoExampleResponse],
    summary="Get order by ID (v2)",
)
async def get_pedido_v2(
    pedido_id: str,
    use_case: PedidoExampleUseCase = Depends(get_pedido_use_case),
) -> ApiResponse[PedidoExampleResponse]:
    """Get single pedido with v2 response.

    **Feature: interface-modules-workflow-analysis**
    **Validates: Requirements 1.1**
    """
    result = await use_case.get(pedido_id)
    if result.is_err():
        raise handle_result_error(result.unwrap_err())
    return ApiResponse(data=result.unwrap())
