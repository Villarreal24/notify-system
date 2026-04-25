from types import SimpleNamespace
from uuid import UUID

import pytest

from models import LogStatus
from services.notifications import CategoryNotFoundError, NotificationService
from strategies.notification_channel import SendResult


class FakeCategoryRepository:
    def __init__(self, exists: bool = True) -> None:
        self.exists = exists

    async def get_by_id(self, category_id: int) -> object | None:
        if not self.exists:
            return None
        return SimpleNamespace(id=category_id, name="Sports")


class FakeUserRepository:
    async def list_by_category(self, category_id: int) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(
                id=UUID("a1b2c3d4-0000-0000-0000-000000000001"),
                email="alice@example.com",
                phone_number="+1234567890",
                channels=[SimpleNamespace(id=2, name="E-Mail")],
            ),
            SimpleNamespace(
                id=UUID("a1b2c3d4-0000-0000-0000-000000000003"),
                email="charlie@example.com",
                phone_number="+1122334455",
                channels=[
                    SimpleNamespace(id=2, name="E-Mail"),
                    SimpleNamespace(id=3, name="Push Notification"),
                ],
            ),
        ]


class FakeLogRepository:
    def __init__(self) -> None:
        self.records: list[dict[str, object]] = []
        self.status_updates: list[dict[str, object]] = []
        self.logs_by_id: dict[UUID, SimpleNamespace] = {}

    async def create(self, **kwargs: object) -> object:
        log_id = UUID(f"b1b2c3d4-0000-0000-0000-{len(self.records) + 1:012d}")
        kwargs.setdefault("id", log_id)
        kwargs.setdefault("channel_id", None)
        kwargs.setdefault("user_id", None)
        kwargs.setdefault("status", LogStatus.PENDING)
        kwargs.setdefault("error_message", None)
        self.records.append(kwargs)
        log = SimpleNamespace(**kwargs)
        self.logs_by_id[log.id] = log
        return log

    async def get_by_id(self, log_id: UUID) -> object | None:
        return self.logs_by_id.get(log_id)

    async def update_status(self, **kwargs: object) -> object:
        self.status_updates.append(kwargs)
        log = self.logs_by_id.get(kwargs["log_id"])
        if log is not None:
            log.status = kwargs["status"]
            log.error_message = kwargs["error_message"]
        return SimpleNamespace(**kwargs)


class FakeSuccessStrategy:
    channel_name = "E-Mail"

    async def send(self, *, user: object, message: str) -> SendResult:
        return SendResult(
            channel_name=self.channel_name,
            recipient=getattr(user, "email", str(user.id)),
            delivered=True,
            detail="ok",
        )


class FakeSuccessChannelFactory:
    def get(self, channel_name: str) -> FakeSuccessStrategy:
        return FakeSuccessStrategy()


class FakeFailingStrategy:
    channel_name = "E-Mail"

    async def send(self, *, user: object, message: str) -> SendResult:
        raise RuntimeError("Simulated provider outage")


class FakeFailingChannelFactory:
    def get(self, channel_name: str) -> FakeFailingStrategy:
        return FakeFailingStrategy()


class FakeMixedChannelFactory:
    def get(self, channel_name: str) -> FakeSuccessStrategy | FakeFailingStrategy:
        if channel_name == "Push Notification":
            return FakeFailingStrategy()
        return FakeSuccessStrategy()


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_notification_service_delivers_to_subscribed_user_channels() -> None:
    log_repository = FakeLogRepository()
    service = NotificationService(
        category_repository=FakeCategoryRepository(),
        user_repository=FakeUserRepository(),
        log_repository=log_repository,
        channel_factory=FakeSuccessChannelFactory(),
    )

    summary = await service.deliver(category_id=1, message="Final score alert")

    assert summary.recipients == 2
    assert summary.deliveries == 3
    assert len(log_repository.records) == 0


@pytest.mark.asyncio
async def test_notification_service_creates_submission_log() -> None:
    log_repository = FakeLogRepository()
    service = NotificationService(
        category_repository=FakeCategoryRepository(),
        user_repository=FakeUserRepository(),
        log_repository=log_repository,
        channel_factory=FakeSuccessChannelFactory(),
    )

    logs = await service.create_pending_delivery_logs(
        category_id=1,
        message="Final score alert",
    )

    assert len(logs) == 3
    assert logs[0].message == "Final score alert"
    assert logs[0].category.name == "Sports"
    assert logs[0].user.email == "alice@example.com"
    assert logs[0].channel.name == "E-Mail"
    assert len(log_repository.records) == 3
    assert {record["user_id"] for record in log_repository.records} == {
        UUID("a1b2c3d4-0000-0000-0000-000000000001"),
        UUID("a1b2c3d4-0000-0000-0000-000000000003"),
    }
    assert {record["channel_id"] for record in log_repository.records} == {2, 3}
    assert log_repository.records[0]["status"] == LogStatus.PENDING


@pytest.mark.asyncio
async def test_notification_service_marks_single_delivery_log_success() -> None:
    log_repository = FakeLogRepository()
    session = FakeSession()
    service = NotificationService(
        category_repository=FakeCategoryRepository(),
        user_repository=FakeUserRepository(),
        log_repository=log_repository,
        channel_factory=FakeSuccessChannelFactory(),
        session=session,
    )
    log = await log_repository.create(
        message="Final score alert",
        category_id=1,
        channel_id=2,
        user_id=UUID("a1b2c3d4-0000-0000-0000-000000000001"),
    )
    log.user = SimpleNamespace(
        id=log.user_id,
        email="alice@example.com",
        phone_number="+1234567890",
    )
    log.channel = SimpleNamespace(id=2, name="E-Mail")

    delivered_log = await service.deliver_pending_log(log_id=log.id)

    assert delivered_log is log
    assert log_repository.status_updates == [
        {
            "log_id": log.id,
            "status": LogStatus.SUCCESS,
            "error_message": None,
        }
    ]
    assert session.commits == 1
    assert session.rollbacks == 0


@pytest.mark.asyncio
async def test_notification_service_processes_pending_logs_as_batch() -> None:
    log_repository = FakeLogRepository()
    session = FakeSession()
    service = NotificationService(
        category_repository=FakeCategoryRepository(),
        user_repository=FakeUserRepository(),
        log_repository=log_repository,
        channel_factory=FakeMixedChannelFactory(),
        session=session,
    )
    email_log = await log_repository.create(
        message="Final score alert",
        category_id=1,
        channel_id=2,
        user_id=UUID("a1b2c3d4-0000-0000-0000-000000000001"),
    )
    email_log.user = SimpleNamespace(
        id=email_log.user_id,
        email="alice@example.com",
        phone_number="+1234567890",
    )
    email_log.channel = SimpleNamespace(id=2, name="E-Mail")
    push_log = await log_repository.create(
        message="Final score alert",
        category_id=1,
        channel_id=3,
        user_id=UUID("a1b2c3d4-0000-0000-0000-000000000003"),
    )
    push_log.user = SimpleNamespace(
        id=push_log.user_id,
        email="charlie@example.com",
        phone_number="+1122334455",
    )
    push_log.channel = SimpleNamespace(id=3, name="Push Notification")

    await service.deliver_pending_logs(log_ids=[email_log.id, push_log.id])

    assert log_repository.status_updates[0]["status"] == LogStatus.SUCCESS
    assert log_repository.status_updates[1]["status"] == LogStatus.FAILED
    assert "Simulated provider outage" in str(
        log_repository.status_updates[1]["error_message"]
    )
    assert session.commits == 1
    assert session.rollbacks == 0


@pytest.mark.asyncio
async def test_notification_service_marks_single_delivery_log_failed() -> None:
    log_repository = FakeLogRepository()
    session = FakeSession()
    service = NotificationService(
        category_repository=FakeCategoryRepository(),
        user_repository=FakeUserRepository(),
        log_repository=log_repository,
        channel_factory=FakeFailingChannelFactory(),
        session=session,
    )
    log = await log_repository.create(
        message="Final score alert",
        category_id=1,
        channel_id=2,
        user_id=UUID("a1b2c3d4-0000-0000-0000-000000000001"),
    )
    log.user = SimpleNamespace(
        id=log.user_id,
        email="alice@example.com",
        phone_number="+1234567890",
    )
    log.channel = SimpleNamespace(id=2, name="E-Mail")

    delivered_log = await service.deliver_pending_log(log_id=log.id)

    assert delivered_log is None
    assert log_repository.status_updates[0]["log_id"] == log.id
    assert log_repository.status_updates[0]["status"] == LogStatus.FAILED
    assert "Simulated provider outage" in str(
        log_repository.status_updates[0]["error_message"]
    )
    assert session.commits == 1
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_notification_service_rejects_unknown_category() -> None:
    service = NotificationService(
        category_repository=FakeCategoryRepository(exists=False),
        user_repository=FakeUserRepository(),
        log_repository=FakeLogRepository(),
        channel_factory=FakeSuccessChannelFactory(),
    )

    with pytest.raises(CategoryNotFoundError):
        await service.deliver(category_id=999, message="Unknown category")
