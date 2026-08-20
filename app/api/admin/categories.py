from fastapi import APIRouter, Depends, status
from prisma.models import User

from app.core.dependencies import check_store_role, require_admin, require_store_member, require_store_role
from app.schemas.category import CategoryResponse, CreateCategoryRequest, UpdateCategoryRequest
from app.services import category_service

router = APIRouter(tags=["Admin"])


@router.get(
    "/admin/stores/{store_id}/categories",
    response_model=list[CategoryResponse],
    summary="List all categories for a store (including inactive)",
)
async def list_categories(store_id: str, membership=Depends(require_store_member)):
    return await category_service.list_categories_for_admin(store_id)


@router.post(
    "/admin/stores/{store_id}/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category",
)
async def create_category(
    store_id: str,
    payload: CreateCategoryRequest,
    membership=Depends(require_store_role("OWNER", "MANAGER")),
):
    return await category_service.create_category(store_id, payload.model_dump())


@router.get(
    "/admin/categories/{category_id}", response_model=CategoryResponse, summary="Get a category"
)
async def get_category(category_id: str, user: User = Depends(require_admin)):
    category = await category_service.get_category_or_404(category_id)
    await check_store_role(user.id, category.storeId)
    return category


@router.patch(
    "/admin/categories/{category_id}", response_model=CategoryResponse, summary="Update a category"
)
async def update_category(
    category_id: str, payload: UpdateCategoryRequest, user: User = Depends(require_admin)
):
    category = await category_service.get_category_or_404(category_id)
    await check_store_role(user.id, category.storeId, allowed_roles=("OWNER", "MANAGER"))
    return await category_service.update_category(
        category_id, payload.model_dump(exclude_unset=True)
    )


@router.delete(
    "/admin/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a category",
)
async def delete_category(category_id: str, user: User = Depends(require_admin)):
    category = await category_service.get_category_or_404(category_id)
    await check_store_role(user.id, category.storeId, allowed_roles=("OWNER", "MANAGER"))
    await category_service.delete_category(category_id)
