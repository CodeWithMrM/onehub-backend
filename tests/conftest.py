"""
Shared pytest fixtures.

These tests exercise routing, validation, and authorization logic
using dependency overrides and mocked Prisma calls, so they don't
require a live database. For full integration coverage against a
real Postgres instance, point DATABASE_URL/DIRECT_DATABASE_URL at a
disposable Neon branch and run `prisma generate && prisma db push`
first — see the README's Testing section.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, require_admin, require_authenticated_user
from app.main import app


def make_user(**overrides):
    defaults = dict(id="user-1", clerkUserId="clerk_1", name="Test User", phone=None, role="CUSTOMER")
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def as_customer():
    """Overrides auth dependencies to simulate a signed-in customer."""
    user = make_user(role="CUSTOMER")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_authenticated_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_authenticated_user, None)


@pytest.fixture
def as_admin():
    """Overrides auth dependencies to simulate a signed-in admin."""
    user = make_user(id="admin-1", clerkUserId="clerk_admin", role="ADMIN")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_authenticated_user] = lambda: user
    app.dependency_overrides[require_admin] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_authenticated_user, None)
    app.dependency_overrides.pop(require_admin, None)


@pytest.fixture
def mock_db(monkeypatch):
    """
    Patches every Prisma model accessor used in this codebase with
    an AsyncMock, so individual tests can set return values without
    touching a real database.
    """
    from app.db import prisma as prisma_module

    mocked = SimpleNamespace()
    for model_name in [
        "user",
        "store",
        "storemember",
        "category",
        "product",
        "productoptiongroup",
        "productoption",
        "order",
        "orderitem",
        "ordercounter",
    ]:
        model_mock = SimpleNamespace(
            find_unique=AsyncMock(return_value=None),
            find_many=AsyncMock(return_value=[]),
            create=AsyncMock(),
            update=AsyncMock(),
            delete=AsyncMock(),
            count=AsyncMock(return_value=0),
        )
        monkeypatch.setattr(prisma_module.db, model_name, model_mock)
        setattr(mocked, model_name, model_mock)

    return mocked
