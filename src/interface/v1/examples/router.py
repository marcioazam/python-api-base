"""API routes for ItemExample and PedidoExample.

Demonstrates:
- FastAPI router setup
- Dependency injection with real repositories
- Request/Response handling
- Error handling
- OpenAPI documentation
- Multi-tenancy support
- Rate limiting
- RBAC protection (optional)

**Feature: example-system-demo**
**Feature: infrastructure-examples-integration-fix**
**Feature: infrastructure-modules-integration-analysis**
**Feature: infrastructure-modules-workflow-analysis**
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 1.3**
"""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.ratelimit import RateLimit, rate_limit, InMemoryRateLimiter, RateLimitConfig
from infrastructure.security.rbac import Permission, RBACUser, get_rbac_service

from application.common.base.dto import ApiResponse, PaginatedResponse
from infrastructure.kafka import create_event_publisher, EventPublisher
from application.examples import (
    # DTOs
    ItemExampleCreate,
    ItemExampleUpdate,
    ItemExampleResponse,
    PedidoExampleCreate,
    PedidoExampleResponse,
    AddItemRequest,
    CancelPedidoRequest,
    # Use Cases
    ItemExampleUseCase,
    PedidoExampleUseCase,
    # Errors
    NotFoundError,
    ValidationError,
)
from infrastructure.db.session import get_async_session
from infrastructure.db.repositories.examples import (
    ItemExampleRepository,
    PedidoExampleRepository,
)

router = APIRouter(prefix="/examples", tags=["Examples"])


# === Dependency Injection with Real Repositories ===


async def get_item_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ItemExampleRepository:
    """Get ItemExampleRepository with injected database session.

    **Feature: infrastructure-examples-integration-fix**
    **Validates: Requirements 2.1, 2.2**
    """
    return ItemExampleRepository(session)


async def get_pedido_repository(
    session: AsyncSession = Depends(get_async_session),
) -> PedidoExampleRepository:
    """Get PedidoExampleRepository with injected database session.

    **Feature: infrastructure-examples-integration-fix**
    **Validates: Requirements 2.1, 2.2**
    """
    return PedidoExampleRepository(session)


def get_event_publisher(request: Request) -> EventPublisher:
    """Get EventPublisher based on Kafka availability.

    **Feature: kafka-workflow-integration**
    **Validates: Requirements 3.4**
    """
    kafka_producer = getattr(request.app.state, "kafka_producer", None)
    return create_event_publisher(kafka_producer)


async def get_item_use_case(
    repo: ItemExampleRepository = Depends(get_item_repository),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> ItemExampleUseCase:
    """Get ItemExampleUseCase with real repository and event publisher.

    **Feature: infrastructure-examples-integration-fix**
    **Feature: kafka-workflow-integration**
    **Validates: Requirements 2.1, 2.2, 2.3, 3.1**
    """
    return ItemExampleUseCase(repository=repo, kafka_publisher=event_publisher)


async def get_pedido_use_case(
    item_repo: ItemExampleRepository = Depends(get_item_repository),
    pedido_repo: PedidoExampleRepository = Depends(get_pedido_repository),
) -> PedidoExampleUseCase:
    """Get PedidoExampleUseCase with real repositories.

    **Feature: infrastructure-examples-integration-fix**
    **Validates: Requirements 2.1, 2.2, 2.3**
    """
    return PedidoExampleUseCase(
        pedido_repo=pedido_repo,
        item_repo=item_repo,
    )


# === Error Handling ===


def handle_result_error(error: Any) -> HTTPException:
    """Convert use case error to HTTP exception."""
    if isinstance(error, NotFoundError):
        return HTTPException(status_code=404, detail=error.message)
    if isinstance(error, ValidationError):
        return HTTPException(status_code=422, detail=error.message)
    return HTTPException(status_code=500, detail=str(error))


# === RBAC Dependencies ===
# **Feature: infrastructure-modules-workflow-analysis**
# **Validates: Requirements 2.1**


def get_current_user_optional(
    x_user_id: str = Header(default="anonymous", alias="X-User-Id"),
    x_user_roles: str = Header(default="viewer", alias="X-User-Roles"),
) -> RBACUser:
    """Get current user from headers (optional authentication).

    For demonstration purposes, user info comes from headers.
    In production, use JWT tokens or OAuth2.

    **Feature: infrastructure-modules-workflow-analysis**
    **Validates: Requirements 2.1**
    """
    roles = [r.strip() for r in x_user_roles.split(",") if r.strip()]
    return RBACUser(id=x_user_id, roles=roles)


def require_write_permission(
    user: RBACUser = Depends(get_current_user_optional),
) -> RBACUser:
    """Require WRITE permission for modifying resources.

    **Feature: infrastructure-modules-workflow-analysis**
    **Validates: Requirements 2.1**
    """
    rbac = get_rbac_service()
    if not rbac.check_permission(user, Permission.WRITE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{Permission.WRITE.value}' required. User roles: {user.roles}",
        )
    return user


def require_delete_permission(
    user: RBACUser = Depends(get_current_user_optional),
) -> RBACUser:
    """Require DELETE permission for deleting resources.

    **Feature: infrastructure-modules-workflow-analysis**
    **Validates: Requirements 2.1**
    """
    rbac = get_rbac_service()
    if not rbac.check_permission(user, Permission.DELETE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{Permission.DELETE.value}' required. User roles: {user.roles}",
        )
    return user


# === ItemExample Routes ===


# Rate limit configurations
# **Feature: infrastructure-modules-integration-analysis**
# **Validates: Requirements 1.3**
READ_RATE_LIMIT = RateLimit(requests=100, window=timedelta(minutes=1))
WRITE_RATE_LIMIT = RateLimit(requests=20, window=timedelta(minutes=1))

# Global rate limiter instance
_rate_limiter: InMemoryRateLimiter[str] | None = None


def get_rate_limiter() -> InMemoryRateLimiter[str]:
    """Get or create global rate limiter for examples."""
    global _rate_limiter
    if _rate_limiter is None:
        config = RateLimitConfig(default_limit=READ_RATE_LIMIT)
        _rate_limiter = InMemoryRateLimiter[str](config)
    return _rate_limiter


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
    use_case: ItemExampleUseCase = Depends(get_item_use_case),
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
        size=page_size,
    )


@router.post(
    "/items",
    response_model=ApiResponse[ItemExampleResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create item",
    description="Create a new ItemExample entity. Requires WRITE permission.",
)
async def create_item(
    data: ItemExampleCreate,
    user: RBACUser = Depends(require_write_permission),
    use_case: ItemExampleUseCase = Depends(get_item_use_case),
) -> ApiResponse[ItemExampleResponse]:
    """Create item with RBAC protection.

    **Feature: infrastructure-modules-workflow-analysis**
    **Validates: Requirements 2.1**
    """
    result = await use_case.create(data, created_by=user.id)
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
    use_case: ItemExampleUseCase = Depends(get_item_use_case),
) -> ApiResponse[ItemExampleResponse]:
    result = await use_case.get(item_id)
    if result.is_err():
        raise handle_result_error(result.unwrap_err())
    return ApiResponse(data=result.unwrap())


@router.put(
    "/items/{item_id}",
    response_model=ApiResponse[ItemExampleResponse],
    summary="Update item",
    description="Update an existing item. Requires WRITE permission.",
)
async def update_item(
    item_id: str,
    data: ItemExampleUpdate,
    user: RBACUser = Depends(require_write_permission),
    use_case: ItemExampleUseCase = Depends(get_item_use_case),
) -> ApiResponse[ItemExampleResponse]:
    """Update item with RBAC protection.

    **Feature: infrastructure-modules-workflow-analysis**
    **Validates: Requirements 2.1**
    """
    result = await use_case.update(item_id, data, updated_by=user.id)
    if result.is_err():
        raise handle_result_error(result.unwrap_err())
    return ApiResponse(data=result.unwrap())


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete item",
    description="Delete an item. Requires DELETE permission.",
)
async def delete_item(
    item_id: str,
    user: RBACUser = Depends(require_delete_permission),
    use_case: ItemExampleUseCase = Depends(get_item_use_case),
) -> None:
    """Delete item with RBAC protection.

    **Feature: infrastructure-modules-workflow-analysis**
    **Validates: Requirements 2.1**
    """
    result = await use_case.delete(item_id, deleted_by=user.id)
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
    use_case: PedidoExampleUseCase = Depends(get_pedido_use_case),
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
        size=page_size,
    )


@router.post(
    "/pedidos",
    response_model=ApiResponse[PedidoExampleResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create order",
    description="Create a new order. Requires WRITE permission.",
)
async def create_pedido(
    data: PedidoExampleCreate,
    user: RBACUser = Depends(require_write_permission),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    use_case: PedidoExampleUseCase = Depends(get_pedido_use_case),
) -> ApiResponse[PedidoExampleResponse]:
    """Create order with RBAC protection.

    **Feature: infrastructure-modules-workflow-analysis**
    **Validates: Requirements 2.1**
    """
    result = await use_case.create(
        data,
        tenant_id=x_tenant_id,
        created_by=user.id,
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
    use_case: PedidoExampleUseCase = Depends(get_pedido_use_case),
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
    use_case: PedidoExampleUseCase = Depends(get_pedido_use_case),
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
    use_case: PedidoExampleUseCase = Depends(get_pedido_use_case),
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
    use_case: PedidoExampleUseCase = Depends(get_pedido_use_case),
) -> ApiResponse[PedidoExampleResponse]:
    result = await use_case.cancel(
        pedido_id,
        reason=data.reason,
        cancelled_by=x_user_id,
    )
    if result.is_err():
        raise handle_result_error(result.unwrap_err())
    return ApiResponse(data=result.unwrap())
