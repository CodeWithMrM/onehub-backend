from fastapi import APIRouter, Depends, Query
from prisma.models import User

from app.core.dependencies import check_store_role, require_admin, require_store_member
from app.core.errors import NotFoundError
from app.core.rate_limit import rate_limit
from app.db.prisma import db
from app.schemas.common import PaginatedResponse
from app.schemas.order import OrderResponse, UpdateOrderStatusRequest
from app.services import order_service

router = APIRouter(tags=["Admin"])


async def _get_order_with_access_check(order_id: str, user_id: str):
    """
    Admin order-detail routes only carry the order id in the path
    (not the store id), so we look the order up first, then verify
    the caller belongs to *its* store before returning anything.
    """
    order = await db.order.find_unique(where={"id": order_id}, include={"items": True})
    if order is None:
        raise NotFoundError("Order not found.", code="ORDER_NOT_FOUND")
    await check_store_role(user_id, order.storeId)
    return order


@router.get(
    "/admin/stores/{store_id}/orders",
    response_model=PaginatedResponse[OrderResponse],
    summary="List orders for a store",
)
async def list_store_orders(
    store_id: str,
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    membership=Depends(require_store_member),
):
    orders, total = await order_service.list_orders_for_store(store_id, status, page, page_size)
    return {"items": orders, "page": page, "pageSize": page_size, "total": total}


@router.get("/admin/orders/{order_id}", response_model=OrderResponse, summary="Get order details")
async def get_order(order_id: str, user: User = Depends(require_admin)):
    return await _get_order_with_access_check(order_id, user.id)


@router.patch(
    "/admin/orders/{order_id}/status",
    response_model=OrderResponse,
    summary="Update an order's status",
    dependencies=[Depends(rate_limit(limit=60, window_seconds=60, scope="admin_mutation"))],
)
async def update_order_status(
    order_id: str, payload: UpdateOrderStatusRequest, user: User = Depends(require_admin)
):
    order = await _get_order_with_access_check(order_id, user.id)
    return await order_service.update_order_status(order_id, order.storeId, payload.status)
