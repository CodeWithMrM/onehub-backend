from fastapi import APIRouter, Query

from app.schemas.common import PaginatedResponse
from app.schemas.product import ProductDetailResponse, ProductListItem
from app.services import product_service, store_service

router = APIRouter(tags=["Public"])


@router.get(
    "/stores/{store_id}/products",
    response_model=PaginatedResponse[ProductListItem],
    summary="List available products for a store",
)
async def list_products(
    store_id: str,
    category_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    await store_service.get_store_or_404(store_id)
    products, total = await product_service.list_available_products(
        store_id=store_id, category_id=category_id, search=search, page=page, page_size=page_size
    )
    return {"items": products, "page": page, "pageSize": page_size, "total": total}


@router.get(
    "/products/{product_id}",
    response_model=ProductDetailResponse,
    summary="Get product details, including customization options",
)
async def get_product(product_id: str):
    return await product_service.get_product_detail_or_404(product_id)
