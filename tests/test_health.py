from unittest.mock import AsyncMock


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db_ok(client, monkeypatch):
    from app import main as main_module

    monkeypatch.setattr(main_module, "check_db_connection", AsyncMock(return_value=True))
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db_unavailable(client, monkeypatch):
    from app import main as main_module

    monkeypatch.setattr(main_module, "check_db_connection", AsyncMock(return_value=False))
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "unavailable"}
