"""
Order business logic.

The single most important rule in this file: the client NEVER
supplies a price. Every price is looked up from the database inside
the same transaction that creates the order, so what the customer
is charged always matches what's actually in the catalog at the
moment of purchase.
"""

from decimal import Decimal

from prisma.models import Order

from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ProductUnavailableError, StoreInactiveError, ValidationAppError
from app.db.prisma import db

# Valid forward status transitions. Cancellation is allowed from any
# non-terminal state; nothing is allowed to move backwards.
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "NEW": {"CONFIRMED", "CANCELLED"},
    "CONFIRMED": {"PREPARING", "CANCELLED"},
    "PREPARING": {"READY", "CANCELLED"},
    "READY": {"COMPLETED", "CANCELLED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
}


async def _generate_order_number(tx, store_id: str) -> str:
    counter = await tx.ordercounter.find_unique(where={"storeId": store_id})
    if counter is None:
        counter = await tx.ordercounter.create(data={"storeId": store_id, "value": 1})
        next_value = 1
    else:
        counter = await tx.ordercounter.update(
            where={"storeId": store_id}, data={"value": {"increment": 1}}
        )
        next_value = counter.value
    return f"OH-{next_value:06d}"


async def create_order(user_id: str, payload, idempotency_key: str | None = None) -> Order:
    # Idempotency: if this user already submitted this exact key,
    # return the order that was created for it instead of creating a
    # duplicate (spec §38 — mobile networks retry requests).
    if idempotency_key:
        existing = await db.order.find_unique(
            where={"userId_idempotencyKey": {"userId": user_id, "idempotencyKey": idempotency_key}},
            include={"items": True},
        )
        if existing is not None:
            return existing

    store = await db.store.find_unique(where={"id": payload.storeId})
    if store is None:
        raise NotFoundError("Store not found.", code="STORE_NOT_FOUND")
    if not store.isActive:
        raise StoreInactiveError("This store is not currently accepting orders.")

    line_items: list[dict] = []
    subtotal = Decimal("0.00")

    for requested_item in payload.items:
        product = await db.product.find_unique(
            where={"id": requested_item.productId},
            include={"optionGroups": {"include": {"options": True}}},
        )
        if product is None:
            raise NotFoundError(
                f"Product {requested_item.productId} not found.", code="PRODUCT_NOT_FOUND"
            )
        if product.storeId != payload.storeId:
            raise ValidationAppError(
                "Product does not belong to the requested store.", code="PRODUCT_STORE_MISMATCH"
            )
        if not product.isAvailable:
            raise ProductUnavailableError(f"{product.name} is currently unavailable.")

        # Validate every requested option belongs to this product and is available.
        valid_option_ids = {
            option.id
            for group in (product.optionGroups or [])
            for option in (group.options or [])
        }
        selected_options = []
        for option_id in requested_item.optionIds:
            if option_id not in valid_option_ids:
                raise ValidationAppError(
                    f"Option {option_id} is not valid for {product.name}.",
                    code="INVALID_OPTION",
                )

        for group in product.optionGroups or []:
            group_selected = [o for o in group.options if o.id in requested_item.optionIds]
            for option in group_selected:
                if not option.isAvailable:
                    raise ProductUnavailableError(
                        f"{option.name} is currently unavailable."
                    )
            if group.required and len(group_selected) < max(group.minSelections, 1):
                raise ValidationAppError(
                    f"{group.name} requires at least one selection.",
                    code="OPTION_GROUP_REQUIRED",
                )
            if len(group_selected) > group.maxSelections:
                raise ValidationAppError(
                    f"{group.name} allows at most {group.maxSelections} selection(s).",
                    code="OPTION_GROUP_TOO_MANY",
                )
            selected_options.extend(group_selected)

        options_total = sum((o.price for o in selected_options), start=Decimal("0.00"))
        unit_price = product.price + options_total
        line_total = unit_price * requested_item.quantity
        subtotal += line_total

        line_items.append(
            {
                "productId": product.id,
                "productName": product.name,
                "unitPrice": unit_price,
                "quantity": requested_item.quantity,
                "customizations": [
                    {"id": o.id, "label": o.name, "priceDelta": str(o.price)}
                    for o in selected_options
                ],
                "total": line_total,
            }
        )

    total = subtotal  # No taxes/delivery/service fees in the MVP.

    async with db.tx() as transaction:
        order_number = await _generate_order_number(transaction, payload.storeId)

        order = await transaction.order.create(
            data={
                "orderNumber": order_number,
                "storeId": payload.storeId,
                "userId": user_id,
                "customerName": payload.customerName,
                "customerPhone": payload.customerPhone,
                "status": "NEW",
                "pickupType": payload.pickupType,
                "pickupTime": payload.pickupTime,
                "notes": payload.notes,
                "subtotal": subtotal,
                "total": total,
                "idempotencyKey": idempotency_key,
            }
        )

        for item in line_items:
            await transaction.orderitem.create(data={**item, "orderId": order.id})

        created_order = await transaction.order.find_unique(
            where={"id": order.id}, include={"items": True}
        )

    return created_order


async def list_orders_for_user(user_id: str, page: int, page_size: int) -> tuple[list[Order], int]:
    total = await db.order.count(where={"userId": user_id})
    orders = await db.order.find_many(
        where={"userId": user_id},
        include={"items": True},
        order={"createdAt": "desc"},
        skip=(page - 1) * page_size,
        take=page_size,
    )
    return orders, total


async def get_order_for_user_or_404(order_id: str, user_id: str) -> Order:
    order = await db.order.find_unique(where={"id": order_id}, include={"items": True})
    if order is None:
        raise NotFoundError("Order not found.", code="ORDER_NOT_FOUND")
    if order.userId != user_id:
        raise ForbiddenError("You do not have access to this order.")
    return order


async def list_orders_for_store(
    store_id: str, status: str | None, page: int, page_size: int
) -> tuple[list[Order], int]:
    where: dict = {"storeId": store_id}
    if status:
        where["status"] = status

    total = await db.order.count(where=where)
    orders = await db.order.find_many(
        where=where,
        include={"items": True},
        order={"createdAt": "desc"},
        skip=(page - 1) * page_size,
        take=page_size,
    )
    return orders, total


async def get_order_for_store_or_404(order_id: str, store_id: str) -> Order:
    order = await db.order.find_unique(where={"id": order_id}, include={"items": True})
    if order is None:
        raise NotFoundError("Order not found.", code="ORDER_NOT_FOUND")
    if order.storeId != store_id:
        raise ForbiddenError("This order does not belong to your store.")
    return order


async def update_order_status(order_id: str, store_id: str, new_status: str) -> Order:
    order = await get_order_for_store_or_404(order_id, store_id)

    allowed_next = _VALID_TRANSITIONS.get(order.status, set())
    if new_status not in allowed_next:
        raise ConflictError(
            f"Cannot move an order from {order.status} to {new_status}.",
            code="INVALID_STATUS_TRANSITION",
        )

    return await db.order.update(where={"id": order_id}, data={"status": new_status})
