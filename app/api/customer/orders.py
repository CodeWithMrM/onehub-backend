from fastapi import APIRouter, Depends, Header, Query
from prisma.models import User

from app.core.dependencies import require_authenticated_user
from app.core.rate_limit import rate_limit
from app.schemas.common import PaginatedResponse
from app.schemas.order import CreateOrderRequest, OrderResponse
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["Customer"])


@router.post(
    "",
    response_model=OrderResponse,
    summary="Place an order",
    dependencies=[Depends(rate_limit(limit=10, window_seconds=60, scope="create_order"))],
)
async def create_order(
    payload: CreateOrderRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: User = Depends(require_authenticated_user),
):
    return await order_service.create_order(user.id, payload, idempotency_key)


@router.get("", response_model=PaginatedResponse[OrderResponse], summary="List my orders")
async def list_my_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(require_authenticated_user),
):
    orders, total = await order_service.list_orders_for_user(user.id, page, page_size)
    return {"items": orders, "page": page, "pageSize": page_size, "total": total}


@router.get("/{order_id}", response_model=OrderResponse, summary="Get one of my orders")
async def get_my_order(order_id: str, user: User = Depends(require_authenticated_user)):
    return await order_service.get_order_for_user_or_404(order_id, user.id)
