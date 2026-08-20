from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.core.errors import ConflictError


def make_membership(role="STAFF", store_id="store-1", user_id="admin-1"):
    return SimpleNamespace(id="member-1", userId=user_id, storeId=store_id, role=role)


def make_product(store_id="store-1"):
    return SimpleNamespace(
        id="prod-1",
        storeId=store_id,
        categoryId="cat-1",
        name="Russian Kota",
        slug="russian-kota",
        description="Tasty",
        price="45.00",
        imageUrl=None,
        isAvailable=True,
        sortOrder=0,
        category=SimpleNamespace(
            id="cat-1",
            name="Kotas",
        ),
    )


VALID_PRODUCT_PAYLOAD = {
    "categoryId": "cat-1",
    "name": "Russian Kota",
    "slug": "russian-kota",
    "description": "Tasty",
    "price": "45.00",
    "isAvailable": True,
    "sortOrder": 0,
}


def test_staff_cannot_create_product(client, as_admin, mock_db):
    mock_db.storemember.find_unique.return_value = make_membership(role="STAFF")

    response = client.post("/api/v1/admin/stores/store-1/products", json=VALID_PRODUCT_PAYLOAD)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_owner_can_create_product(client, as_admin, mock_db, monkeypatch):
    mock_db.storemember.find_unique.return_value = make_membership(role="OWNER")

    from app.services import product_service

    monkeypatch.setattr(
        product_service, "create_product", AsyncMock(return_value=make_product())
    )

    response = client.post("/api/v1/admin/stores/store-1/products", json=VALID_PRODUCT_PAYLOAD)
    assert response.status_code == 201


def test_manager_can_edit_product(client, as_admin, mock_db, monkeypatch):
    mock_db.storemember.find_unique.return_value = make_membership(role="MANAGER")

    from app.services import product_service

    monkeypatch.setattr(
        product_service, "get_product_or_404", AsyncMock(return_value=make_product())
    )
    monkeypatch.setattr(
        product_service, "update_product", AsyncMock(return_value=make_product())
    )

    response = client.patch("/api/v1/admin/products/prod-1", json={"price": "50.00"})
    assert response.status_code == 200


def test_admin_cannot_access_another_stores_dashboard(client, as_admin, mock_db):
    # No membership row exists for this admin at this store.
    mock_db.storemember.find_unique.return_value = None

    response = client.get("/api/v1/admin/stores/store-b/dashboard")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_admin_can_view_store_orders(client, as_admin, mock_db, monkeypatch):
    mock_db.storemember.find_unique.return_value = make_membership(role="STAFF")

    from app.services import order_service

    monkeypatch.setattr(
        order_service, "list_orders_for_store", AsyncMock(return_value=([], 0))
    )

    response = client.get("/api/v1/admin/stores/store-1/orders")
    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "pageSize": 20, "total": 0}


def test_invalid_order_status_transition_is_rejected(client, as_admin, mock_db, monkeypatch):
    order = SimpleNamespace(id="order-1", storeId="store-1", status="COMPLETED")
    mock_db.order.find_unique.return_value = order
    mock_db.storemember.find_unique.return_value = make_membership(role="OWNER")

    from app.services import order_service

    monkeypatch.setattr(
        order_service,
        "update_order_status",
        AsyncMock(
            side_effect=ConflictError(
                "Cannot move an order from COMPLETED to PREPARING.",
                code="INVALID_STATUS_TRANSITION",
            )
        ),
    )

    response = client.patch(
        "/api/v1/admin/orders/order-1/status", json={"status": "PREPARING"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"
