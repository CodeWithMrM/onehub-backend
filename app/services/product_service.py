from prisma.models import Product, ProductOption, ProductOptionGroup

from app.core.errors import ConflictError, NotFoundError
from app.db.prisma import db


async def list_available_products(
    store_id: str,
    category_id: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Product], int]:
    where: dict = {
        "storeId": store_id,
        "isAvailable": True,
        "store": {"isActive": True},
        "category": {"isActive": True},
    }
    if category_id:
        where["categoryId"] = category_id
    if search:
        where["OR"] = [
            {"name": {"contains": search, "mode": "insensitive"}},
            {"description": {"contains": search, "mode": "insensitive"}},
        ]

    total = await db.product.count(where=where)
    products = await db.product.find_many(
        where=where,
        include={"category": True},
        order=[{"sortOrder": "asc"}, {"createdAt": "desc"}],
        skip=(page - 1) * page_size,
        take=page_size,
    )
    return products, total


async def get_product_detail_or_404(product_id: str) -> Product:
    product = await db.product.find_unique(
        where={"id": product_id},
        include={
            "category": True,
            "optionGroups": {
                "include": {"options": True},
                "order_by": {"sortOrder": "asc"},
            },
        },
    )
    if product is None:
        raise NotFoundError("Product not found.", code="PRODUCT_NOT_FOUND")

    # Only expose available options to customers.
    if product.optionGroups:
        for group in product.optionGroups:
            group.options = [o for o in (group.options or []) if o.isAvailable]

    return product


# ── Admin ────────────────────────────────────────────────────────


async def list_products_for_admin(store_id: str) -> list[Product]:
    return await db.product.find_many(
        where={"storeId": store_id},
        include={"category": True},
        order=[{"sortOrder": "asc"}, {"createdAt": "desc"}],
    )


async def get_product_or_404(product_id: str) -> Product:
    product = await db.product.find_unique(where={"id": product_id})
    if product is None:
        raise NotFoundError("Product not found.", code="PRODUCT_NOT_FOUND")
    return product


async def create_product(store_id: str, data: dict) -> Product:
    existing = await db.product.find_unique(
        where={"storeId_slug": {"storeId": store_id, "slug": data["slug"]}}
    )
    if existing is not None:
        raise ConflictError("A product with this slug already exists.", code="PRODUCT_SLUG_TAKEN")

    return await db.product.create(data={**data, "storeId": store_id})


async def update_product(product_id: str, data: dict) -> Product:
    product = await get_product_or_404(product_id)
    new_slug = data.get("slug")
    if new_slug and new_slug != product.slug:
        existing = await db.product.find_unique(
            where={"storeId_slug": {"storeId": product.storeId, "slug": new_slug}}
        )
        if existing is not None:
            raise ConflictError(
                "A product with this slug already exists.", code="PRODUCT_SLUG_TAKEN"
            )

    return await db.product.update(
        where={"id": product_id}, data={k: v for k, v in data.items() if v is not None}
    )


async def delete_product(product_id: str) -> None:
    await get_product_or_404(product_id)
    await db.product.delete(where={"id": product_id})


# ── Option groups / options ────────────────────────────────────


async def create_option_group(product_id: str, data: dict) -> ProductOptionGroup:
    await get_product_or_404(product_id)
    return await db.productoptiongroup.create(data={**data, "productId": product_id})


async def get_option_group_or_404(group_id: str) -> ProductOptionGroup:
    group = await db.productoptiongroup.find_unique(where={"id": group_id})
    if group is None:
        raise NotFoundError("Option group not found.", code="OPTION_GROUP_NOT_FOUND")
    return group


async def update_option_group(group_id: str, data: dict) -> ProductOptionGroup:
    await get_option_group_or_404(group_id)
    return await db.productoptiongroup.update(
        where={"id": group_id}, data={k: v for k, v in data.items() if v is not None}
    )


async def delete_option_group(group_id: str) -> None:
    await get_option_group_or_404(group_id)
    await db.productoptiongroup.delete(where={"id": group_id})


async def create_option(group_id: str, data: dict) -> ProductOption:
    await get_option_group_or_404(group_id)
    return await db.productoption.create(data={**data, "groupId": group_id})


async def get_option_or_404(option_id: str) -> ProductOption:
    option = await db.productoption.find_unique(where={"id": option_id})
    if option is None:
        raise NotFoundError("Option not found.", code="OPTION_NOT_FOUND")
    return option


async def update_option(option_id: str, data: dict) -> ProductOption:
    await get_option_or_404(option_id)
    return await db.productoption.update(
        where={"id": option_id}, data={k: v for k, v in data.items() if v is not None}
    )


async def delete_option(option_id: str) -> None:
    await get_option_or_404(option_id)
    await db.productoption.delete(where={"id": option_id})
