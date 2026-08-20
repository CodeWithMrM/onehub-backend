from datetime import datetime, time, timezone

from prisma.models import Store

from app.core.errors import NotFoundError
from app.db.prisma import db


async def list_active_stores() -> list[Store]:
    return await db.store.find_many(where={"isActive": True}, order={"name": "asc"})


async def get_store_or_404(store_id: str) -> Store:
    store = await db.store.find_unique(where={"id": store_id})
    if store is None:
        raise NotFoundError("Store not found.", code="STORE_NOT_FOUND")
    return store


async def list_stores_for_admin(user_id: str) -> list[Store]:
    memberships = await db.storemember.find_many(
        where={"userId": user_id}, include={"store": True}
    )
    return [m.store for m in memberships if m.store is not None]


async def get_dashboard(store_id: str) -> dict:
    today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)

    new_orders = await db.order.count(where={"storeId": store_id, "status": "NEW"})
    preparing_orders = await db.order.count(where={"storeId": store_id, "status": "PREPARING"})
    ready_orders = await db.order.count(where={"storeId": store_id, "status": "READY"})

    todays_orders = await db.order.find_many(
        where={"storeId": store_id, "createdAt": {"gte": today_start}}
    )
    today_revenue = sum((o.total for o in todays_orders), start=0)

    return {
        "newOrders": new_orders,
        "preparingOrders": preparing_orders,
        "readyOrders": ready_orders,
        "todayOrders": len(todays_orders),
        "todayRevenue": float(today_revenue),
    }
