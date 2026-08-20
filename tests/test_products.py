from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.errors import NotFoundError


def make_store(**overrides):
    defaults = dict(
        id="store-1", name="Mama's Kota", slug="mamas-kota", description=None,
        phone=None, address=None, isActive=True,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_product(**overrides):
    defaults = dict(
        id="prod-1", name="Russian Kota", slug="russian-kota",
        description="Tasty", price="45.00", imageUrl=None, isAvailable=True,
        category=SimpleNamespace(id="cat-1", name="Kotas"),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_list_products_empty_store_returns_empty_list_not_error(client, monkeypatch):
    from app.api.public import products as products_module
    from app.services import store_service

    monkeypatch.setattr(store_service, "get_store_or_404", AsyncMock(return_value=make_store()))
    monkeypatch.setattr(
        products_module.product_service,
        "list_available_products",
        AsyncMock(return_value=([], 0)),
    )

    response = client.get("/api/v1/stores/store-1/products")
    assert response.status_code == 200
    body = response.json()
    assert body == {"items": [], "page": 1, "pageSize": 20, "total": 0}


def test_list_products_with_results(client, monkeypatch):
    from app.api.public import products as products_module
    from app.services import store_service

    monkeypatch.setattr(store_service, "get_store_or_404", AsyncMock(return_value=make_store()))
    monkeypatch.setattr(
        products_module.product_service,
        "list_available_products",
        AsyncMock(return_value=([make_product()], 1)),
    )

    response = client.get("/api/v1/stores/store-1/products?search=russian")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Russian Kota"


def test_get_product_not_found_returns_consistent_error_shape(client, monkeypatch):
    from app.services import product_service

    monkeypatch.setattr(
        product_service,
        "get_product_detail_or_404",
        AsyncMock(side_effect=NotFoundError("Product not found.", code="PRODUCT_NOT_FOUND")),
    )

    response = client.get("/api/v1/products/missing-id")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "PRODUCT_NOT_FOUND", "message": "Product not found."}}


def test_store_not_found_returns_404(client, monkeypatch):
    from app.services import store_service

    monkeypatch.setattr(
        store_service,
        "get_store_or_404",
        AsyncMock(side_effect=NotFoundError("Store not found.", code="STORE_NOT_FOUND")),
    )

    response = client.get("/api/v1/stores/missing-store/products")
    assert response.status_code == 404
