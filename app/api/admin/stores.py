from fastapi import APIRouter, Depends
from prisma.models import User

from app.core.dependencies import require_admin, require_store_member
from app.schemas.store import StoreDashboardResponse, StoreResponse
from app.services import store_service

router = APIRouter(prefix="/admin/stores", tags=["Admin"])


@router.get("", response_model=list[StoreResponse], summary="List stores I belong to")
async def list_my_stores(user: User = Depends(require_admin)):
    return await store_service.list_stores_for_admin(user.id)


@router.get(
    "/{store_id}/dashboard",
    response_model=StoreDashboardResponse,
    summary="Basic order/revenue counts for today",
)
async def get_dashboard(store_id: str, membership=Depends(require_store_member)):
    return await store_service.get_dashboard(store_id)
