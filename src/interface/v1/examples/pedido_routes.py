"""Pedido API routes.

**Feature: example-system-demo**
**Validates: Requirements 2.1, 2.2, 2.3, 2.4**
"""

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from application.common.dto import ApiResponse, PaginatedResponse
from application.examples import (
    AddItemRequest,
    CancelPedidoRequest,
    NotFoundError,
    PedidoExampleCreate,
    PedidoExampleResponse,
    PedidoExampleUseCase,
    ValidationError,
)
from infrastructure.security.rbac import RBACUser
from interface.v1.examples.dependencies import (
    get_pedido_use_case,
    require_write_permission,
)

router = APIRouter()


def handle_result_error(error: Any) -> HTTPException:
    """Convert use case error to HTTP exception."""
    if isinstance(error, NotFoundError):
        return HTTPException(status_code=404, detail=error.message)
    if isinstance(error, ValidationError):
        return HTTPException(status_code=422, detail=error.message)
    return HTTPException(status_code=500, detail=str(error))


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
    """Create order with RBAC protection."""
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
