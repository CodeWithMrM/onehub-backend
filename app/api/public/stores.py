from fastapi import APIRouter

from app.schemas.store import StoreResponse
from app.services import store_service

router = APIRouter(prefix="/stores", tags=["Public"])


@router.get("", response_model=list[StoreResponse], summary="List active stores")
async def list_stores():
    return await store_service.list_active_stores()


@router.get("/{store_id}", response_model=StoreResponse, summary="Get a store")
async def get_store(store_id: str):
    return await store_service.get_store_or_404(store_id)
