from fastapi import APIRouter, Depends, status
from prisma.models import User

from app.core.dependencies import check_store_role, require_admin, require_store_member, require_store_role
from app.schemas.product import (
    CreateOptionGroupRequest,
    CreateOptionRequest,
    CreateProductRequest,
    ProductDetailResponse,
    ProductListItem,
    ProductOptionGroupResponse,
    ProductOptionResponse,
    UpdateOptionGroupRequest,
    UpdateOptionRequest,
    UpdateProductRequest,
)
from app.services import product_service

router = APIRouter(tags=["Admin"])


@router.get(
    "/admin/stores/{store_id}/products",
    response_model=list[ProductListItem],
    summary="List all products for a store (including unavailable)",
)
async def list_products(store_id: str, membership=Depends(require_store_member)):
    return await product_service.list_products_for_admin(store_id)


@router.post(
    "/admin/stores/{store_id}/products",
    response_model=ProductListItem,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product",
)
async def create_product(
    store_id: str,
    payload: CreateProductRequest,
    membership=Depends(require_store_role("OWNER", "MANAGER")),
):
    return await product_service.create_product(store_id, payload.model_dump())


@router.get(
    "/admin/products/{product_id}",
    response_model=ProductDetailResponse,
    summary="Get full product details for editing",
)
async def get_product(product_id: str, user: User = Depends(require_admin)):
    product = await product_service.get_product_or_404(product_id)
    await check_store_role(user.id, product.storeId)
    return await product_service.get_product_detail_or_404(product_id)


@router.patch(
    "/admin/products/{product_id}", response_model=ProductListItem, summary="Update a product"
)
async def update_product(
    product_id: str, payload: UpdateProductRequest, user: User = Depends(require_admin)
):
    product = await product_service.get_product_or_404(product_id)
    await check_store_role(user.id, product.storeId, allowed_roles=("OWNER", "MANAGER"))
    return await product_service.update_product(
        product_id, payload.model_dump(exclude_unset=True)
    )


@router.delete(
    "/admin/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product",
)
async def delete_product(product_id: str, user: User = Depends(require_admin)):
    product = await product_service.get_product_or_404(product_id)
    await check_store_role(user.id, product.storeId, allowed_roles=("OWNER", "MANAGER"))
    await product_service.delete_product(product_id)


# ── Option groups / options ────────────────────────────────────


@router.post(
    "/admin/products/{product_id}/option-groups",
    response_model=ProductOptionGroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a customization group to a product",
)
async def create_option_group(
    product_id: str, payload: CreateOptionGroupRequest, user: User = Depends(require_admin)
):
    product = await product_service.get_product_or_404(product_id)
    await check_store_role(user.id, product.storeId, allowed_roles=("OWNER", "MANAGER"))
    return await product_service.create_option_group(product_id, payload.model_dump())


@router.patch(
    "/admin/option-groups/{group_id}",
    response_model=ProductOptionGroupResponse,
    summary="Update a customization group",
)
async def update_option_group(
    group_id: str, payload: UpdateOptionGroupRequest, user: User = Depends(require_admin)
):
    group = await product_service.get_option_group_or_404(group_id)
    product = await product_service.get_product_or_404(group.productId)
    await check_store_role(user.id, product.storeId, allowed_roles=("OWNER", "MANAGER"))
    return await product_service.update_option_group(
        group_id, payload.model_dump(exclude_unset=True)
    )


@router.delete(
    "/admin/option-groups/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a customization group",
)
async def delete_option_group(group_id: str, user: User = Depends(require_admin)):
    group = await product_service.get_option_group_or_404(group_id)
    product = await product_service.get_product_or_404(group.productId)
    await check_store_role(user.id, product.storeId, allowed_roles=("OWNER", "MANAGER"))
    await product_service.delete_option_group(group_id)


@router.post(
    "/admin/option-groups/{group_id}/options",
    response_model=ProductOptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an option to a customization group",
)
async def create_option(
    group_id: str, payload: CreateOptionRequest, user: User = Depends(require_admin)
):
    group = await product_service.get_option_group_or_404(group_id)
    product = await product_service.get_product_or_404(group.productId)
    await check_store_role(user.id, product.storeId, allowed_roles=("OWNER", "MANAGER"))
    return await product_service.create_option(group_id, payload.model_dump())


@router.patch(
    "/admin/options/{option_id}", response_model=ProductOptionResponse, summary="Update an option"
)
async def update_option(
    option_id: str, payload: UpdateOptionRequest, user: User = Depends(require_admin)
):
    option = await product_service.get_option_or_404(option_id)
    group = await product_service.get_option_group_or_404(option.groupId)
    product = await product_service.get_product_or_404(group.productId)
    await check_store_role(user.id, product.storeId, allowed_roles=("OWNER", "MANAGER"))
    return await product_service.update_option(option_id, payload.model_dump(exclude_unset=True))


@router.delete(
    "/admin/options/{option_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an option",
)
async def delete_option(option_id: str, user: User = Depends(require_admin)):
    option = await product_service.get_option_or_404(option_id)
    group = await product_service.get_option_group_or_404(option.groupId)
    product = await product_service.get_product_or_404(group.productId)
    await check_store_role(user.id, product.storeId, allowed_roles=("OWNER", "MANAGER"))
    await product_service.delete_option(option_id)
