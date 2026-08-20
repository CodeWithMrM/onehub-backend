from fastapi import APIRouter

from app.schemas.category import CategoryResponse
from app.services import category_service, store_service

router = APIRouter(prefix="/stores", tags=["Public"])


@router.get(
    "/{store_id}/categories",
    response_model=list[CategoryResponse],
    summary="List active categories for a store",
)
async def list_categories(store_id: str):
    await store_service.get_store_or_404(store_id)
    return await category_service.list_active_categories(store_id)
