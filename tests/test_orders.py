from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.core.errors import ForbiddenError, NotFoundError, ProductUnavailableError


VALID_PAYLOAD = {
    "storeId": "store-1",
    "customerName": "John",
    "customerPhone": "0712345678",
    "pickupType": "ASAP",
    "notes": "Extra sauce",
    "items": [{"productId": "prod-1", "quantity": 2, "optionIds": []}],
}


def test_create_order_requires_authentication(client):
    response = client.post("/api/v1/orders", json=VALID_PAYLOAD)
    assert response.status_code == 401


def test_create_order_rejects_empty_cart(client, as_customer):
    payload = {**VALID_PAYLOAD, "items": []}
    response = client.post("/api/v1/orders", json=payload)
    assert response.status_code == 422


def test_create_order_rejects_invalid_quantity(client, as_customer):
    payload = {**VALID_PAYLOAD, "items": [{"productId": "prod-1", "quantity": 0, "optionIds": []}]}
    response = client.post("/api/v1/orders", json=payload)
    assert response.status_code == 422

    payload_too_many = {
        **VALID_PAYLOAD,
        "items": [{"productId": "prod-1", "quantity": 999, "optionIds": []}],
    }
    response2 = client.post("/api/v1/orders", json=payload_too_many)
    assert response2.status_code == 422


def test_create_order_rejects_unknown_product(client, as_customer, monkeypatch):
    from app.api.customer import orders as orders_module

    monkeypatch.setattr(
        orders_module.order_service,
        "create_order",
        AsyncMock(side_effect=NotFoundError("Product prod-1 not found.", code="PRODUCT_NOT_FOUND")),
    )
    response = client.post("/api/v1/orders", json=VALID_PAYLOAD)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


def test_create_order_rejects_unavailable_product(client, as_customer, monkeypatch):
    from app.api.customer import orders as orders_module

    monkeypatch.setattr(
        orders_module.order_service,
        "create_order",
        AsyncMock(side_effect=ProductUnavailableError("Russian Kota is currently unavailable.")),
    )
    response = client.post("/api/v1/orders", json=VALID_PAYLOAD)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PRODUCT_UNAVAILABLE"


def test_create_order_never_trusts_client_supplied_price(client, as_customer, monkeypatch):
    """
    Even if a malicious client includes price/subtotal/total fields,
    the request schema doesn't define them, so Pydantic silently
    drops them — the service layer never sees or uses them.
    """
    from app.api.customer import orders as orders_module

    captured_payload = {}

    async def fake_create_order(user_id, payload, idempotency_key=None):
        captured_payload["payload"] = payload
        return SimpleNamespace(
            id="order-1", orderNumber="OH-000001", storeId="store-1", userId=user_id,
            customerName=payload.customerName, customerPhone=payload.customerPhone,
            status="NEW", pickupType=payload.pickupType, pickupTime=None, notes=payload.notes,
            subtotal="90.00", total="90.00", createdAt="2026-01-01T00:00:00Z", items=[],
        )

    monkeypatch.setattr(orders_module.order_service, "create_order", fake_create_order)

    malicious_payload = {**VALID_PAYLOAD, "price": 1, "subtotal": 1, "total": 1}
    response = client.post("/api/v1/orders", json=malicious_payload)
    assert response.status_code == 200
    assert not hasattr(captured_payload["payload"], "price")
    assert not hasattr(captured_payload["payload"], "total")


def test_get_order_enforces_ownership(client, as_customer, monkeypatch):
    from app.api.customer import orders as orders_module

    monkeypatch.setattr(
        orders_module.order_service,
        "get_order_for_user_or_404",
        AsyncMock(side_effect=ForbiddenError("You do not have access to this order.")),
    )
    response = client.get("/api/v1/orders/someone-elses-order")
    assert response.status_code == 403
