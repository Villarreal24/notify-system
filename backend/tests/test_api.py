from collections.abc import AsyncIterator
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID

from fastapi.testclient import TestClient

import api.routes as routes
from api.dependencies import (
    get_catalog_service,
    get_log_service,
    get_notification_service,
)
from main import app
from models import LogStatus
from schemas.notifications import NotificationLogRead
from services.notifications import CategoryNotFoundError


class FakeCatalogService:
    async def list_categories(self) -> list[object]:
        return [
            type("Category", (), {"id": 1, "name": "Sports"})(),
            type("Category", (), {"id": 2, "name": "Finance"})(),
        ]

    async def list_channels(self) -> list[object]:
        return [
            type("Channel", (), {"id": 1, "name": "SMS"})(),
            type("Channel", (), {"id": 2, "name": "E-Mail"})(),
        ]


class FakeLogService:
    async def list_recent(self, limit: int = 50) -> list[NotificationLogRead]:
        return []


class FakeNotificationService:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def create_pending_delivery_logs(
        self, *, category_id: int, message: str
    ) -> list[object]:
        if category_id == 999:
            raise CategoryNotFoundError("Category 999 does not exist")
        return [
            SimpleNamespace(
                id=UUID("b1b2c3d4-0000-0000-0000-000000000001"),
                message=message,
                category_id=category_id,
                category=SimpleNamespace(id=category_id, name="Sports"),
                channel_id=2,
                channel=SimpleNamespace(id=2, name="E-Mail"),
                user_id=UUID("a1b2c3d4-0000-0000-0000-000000000001"),
                user=SimpleNamespace(
                    id=UUID("a1b2c3d4-0000-0000-0000-000000000001"),
                    name="Alice Johnson",
                ),
                status=LogStatus.PENDING,
                error_message=None,
                created_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
            ),
            SimpleNamespace(
                id=UUID("b1b2c3d4-0000-0000-0000-000000000002"),
                message=message,
                category_id=category_id,
                category=SimpleNamespace(id=category_id, name="Sports"),
                channel_id=3,
                channel=SimpleNamespace(id=3, name="Push Notification"),
                user_id=UUID("a1b2c3d4-0000-0000-0000-000000000003"),
                user=SimpleNamespace(
                    id=UUID("a1b2c3d4-0000-0000-0000-000000000003"),
                    name="Charlie Brown",
                ),
                status=LogStatus.PENDING,
                error_message=None,
                created_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
            ),
        ]

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


async def override_catalog_service() -> AsyncIterator[FakeCatalogService]:
    yield FakeCatalogService()


async def override_log_service() -> AsyncIterator[FakeLogService]:
    yield FakeLogService()


async def override_notification_service() -> AsyncIterator[FakeNotificationService]:
    yield FakeNotificationService()


def test_health_liveness_does_not_require_database() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_read_routes_return_catalogs() -> None:
    app.dependency_overrides[get_catalog_service] = override_catalog_service
    app.dependency_overrides[get_log_service] = override_log_service

    with TestClient(app) as client:
        categories = client.get("/categories")
        channels = client.get("/channels")
        logs = client.get("/notification-logs")

    app.dependency_overrides.clear()

    assert categories.status_code == 200
    assert categories.json()[0]["name"] == "Sports"
    assert channels.status_code == 200
    assert channels.json()[1]["name"] == "E-Mail"
    assert logs.status_code == 200
    assert logs.json() == []


def test_create_notification_returns_accepted(monkeypatch) -> None:
    app.dependency_overrides[get_notification_service] = override_notification_service
    delivered: list[list[UUID]] = []

    async def fake_background(log_ids: list[UUID]) -> None:
        delivered.append(log_ids)

    monkeypatch.setattr(routes, "deliver_notification_background", fake_background)

    with TestClient(app) as client:
        response = client.post(
            "/notifications",
            json={"category_id": 1, "message": "Sports update"},
        )

    app.dependency_overrides.clear()

    log_ids = [
        UUID("b1b2c3d4-0000-0000-0000-000000000001"),
        UUID("b1b2c3d4-0000-0000-0000-000000000002"),
    ]
    body = response.json()

    assert response.status_code == 202
    assert len(body) == 2
    assert body[0]["message"] == "Sports update"
    assert body[0]["category_name"] == "Sports"
    assert body[0]["channel_name"] == "E-Mail"
    assert body[0]["user_name"] == "Alice Johnson"
    assert body[0]["status"] == "PENDING"
    assert body[0]["error_message"] is None
    assert delivered == [log_ids]


def test_validation_error_returns_code() -> None:
    with TestClient(app) as client:
        response = client.post("/notifications", json={})

    assert response.status_code == 422
    body = response.json()
    assert body.get("code") == "VALIDATION_ERROR"
    assert isinstance(body.get("detail"), list)


def test_create_notification_rejects_unknown_category() -> None:
    app.dependency_overrides[get_notification_service] = override_notification_service

    with TestClient(app) as client:
        response = client.post(
            "/notifications",
            json={"category_id": 999, "message": "Unknown"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 404
    data = response.json()
    assert data.get("code") == "CATEGORY_NOT_FOUND"
    assert "999" in data.get("detail", "")
