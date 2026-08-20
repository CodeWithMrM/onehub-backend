from prisma.models import Category

from app.core.errors import ConflictError, NotFoundError
from app.db.prisma import db


async def list_active_categories(store_id: str) -> list[Category]:
    return await db.category.find_many(
        where={"storeId": store_id, "isActive": True},
        order=[{"sortOrder": "asc"}, {"name": "asc"}],
    )


async def list_categories_for_admin(store_id: str) -> list[Category]:
    return await db.category.find_many(
        where={"storeId": store_id},
        order=[{"sortOrder": "asc"}, {"name": "asc"}],
    )


async def get_category_or_404(category_id: str) -> Category:
    category = await db.category.find_unique(where={"id": category_id})
    if category is None:
        raise NotFoundError("Category not found.", code="CATEGORY_NOT_FOUND")
    return category


async def create_category(store_id: str, data: dict) -> Category:
    existing = await db.category.find_unique(
        where={"storeId_slug": {"storeId": store_id, "slug": data["slug"]}}
    )
    if existing is not None:
        raise ConflictError("A category with this slug already exists.", code="CATEGORY_SLUG_TAKEN")

    return await db.category.create(data={**data, "storeId": store_id})


async def update_category(category_id: str, data: dict) -> Category:
    category = await get_category_or_404(category_id)
    new_slug = data.get("slug")
    if new_slug and new_slug != category.slug:
        existing = await db.category.find_unique(
            where={"storeId_slug": {"storeId": category.storeId, "slug": new_slug}}
        )
        if existing is not None:
            raise ConflictError(
                "A category with this slug already exists.", code="CATEGORY_SLUG_TAKEN"
            )

    return await db.category.update(
        where={"id": category_id}, data={k: v for k, v in data.items() if v is not None}
    )


async def delete_category(category_id: str) -> None:
    await get_category_or_404(category_id)
    await db.category.delete(where={"id": category_id})
