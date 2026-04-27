import asyncio
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from uuid import UUID

import pytest

from models import LogStatus, User
from repositories.categories import CategoryRepository
from repositories.logs import NotificationLogRepository
from repositories.users import UserRepository
from services.notifications import CategoryNotFoundError, NotificationService
from strategies.factory import ChannelFactory
from strategies.notification_channel import SendResult

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class FakeCategoryRepository:
    def __init__(self, exists: bool = True) -> None:
        self.exists = exists

    async def get_by_id(self, category_id: int) -> SimpleNamespace | None:
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

    async def create(
        self,
        *,
        message: str,
        category_id: int,
        channel_id: int,
        user_id: UUID,
    ) -> SimpleNamespace:
        log_id = UUID(f"b1b2c3d4-0000-0000-0000-{len(self.records) + 1:012d}")
        record: dict[str, object] = {
            "id": log_id,
            "message": message,
            "category_id": category_id,
            "channel_id": channel_id,
            "user_id": user_id,
            "status": LogStatus.PENDING,
            "error_message": None,
        }
        self.records.append(record)
        log = SimpleNamespace(**record)
        self.logs_by_id[log.id] = log
        return log

    async def get_by_id(self, log_id: UUID) -> SimpleNamespace | None:
        return self.logs_by_id.get(log_id)

    async def update_status(
        self,
        *,
        log_id: UUID,
        status: LogStatus,
        error_message: str | None = None,
    ) -> SimpleNamespace | None:
        update: dict[str, object] = {
            "log_id": log_id,
            "status": status,
            "error_message": error_message,
        }
        self.status_updates.append(update)
        log = self.logs_by_id.get(log_id)
        if log is not None:
            log.status = status
            log.error_message = error_message
        return log


class FakeSuccessStrategy:
    channel_name = "E-Mail"

    async def send(self, *, user: User, message: str) -> SendResult:
        return SendResult(
            channel_name=self.channel_name,
            recipient=user.email,
            delivered=True,
            detail="ok",
        )


class FakeSuccessChannelFactory:
    def get(self, channel_name: str) -> FakeSuccessStrategy:
        return FakeSuccessStrategy()


class FakeFailingStrategy:
    channel_name = "E-Mail"

    async def send(self, *, user: User, message: str) -> SendResult:
        raise RuntimeError("Simulated provider outage")


class FakeFailingChannelFactory:
    def get(self, channel_name: str) -> FakeFailingStrategy:
        return FakeFailingStrategy()


class FakeMixedChannelFactory:
    def get(self, channel_name: str) -> FakeSuccessStrategy | FakeFailingStrategy:
        if channel_name == "Push Notification":
            return FakeFailingStrategy()
        return FakeSuccessStrategy()


class FakeConcurrentStrategy:
    channel_name = "E-Mail"

    def __init__(self) -> None:
        self.in_flight = 0
        self.max_in_flight = 0

    async def send(self, *, user: User, message: str) -> SendResult:
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            await asyncio.sleep(0.01)
            return SendResult(
                channel_name=self.channel_name,
                recipient=user.email,
                delivered=True,
                detail="ok",
            )
        finally:
            self.in_flight -= 1


class FakeConcurrentChannelFactory:
    def __init__(self) -> None:
        self.strategy = FakeConcurrentStrategy()

    def get(self, channel_name: str) -> FakeConcurrentStrategy:
        return self.strategy


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def make_service(
    *,
    category_repository: FakeCategoryRepository | None = None,
    user_repository: FakeUserRepository | None = None,
    log_repository: FakeLogRepository | None = None,
    channel_factory: (
        FakeSuccessChannelFactory
        | FakeFailingChannelFactory
        | FakeMixedChannelFactory
        | FakeConcurrentChannelFactory
        | None
    ) = None,
    session: FakeSession | None = None,
) -> NotificationService:
    return NotificationService(
        category_repository=cast(
            CategoryRepository, category_repository or FakeCategoryRepository()
        ),
        user_repository=cast(UserRepository, user_repository or FakeUserRepository()),
        log_repository=cast(NotificationLogRepository, log_repository or FakeLogRepository()),
        channel_factory=cast(ChannelFactory, channel_factory or FakeSuccessChannelFactory()),
        session=cast("AsyncSession | None", session),
    )


@pytest.mark.asyncio
async def test_notification_service_creates_submission_log() -> None:
    log_repository = FakeLogRepository()
    service = make_service(
        log_repository=log_repository,
        channel_factory=FakeSuccessChannelFactory(),
    )

    logs = await service.create_pending_delivery_logs(
        category_id=1,
        message="Final score alert",
    )

    assert len(logs) == 3
    assert logs[0].message == "Final score alert"
    assert logs[0].category is not None
    assert logs[0].user is not None
    assert logs[0].channel is not None
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
async def test_notification_service_processes_pending_logs_as_batch() -> None:
    log_repository = FakeLogRepository()
    session = FakeSession()
    service = make_service(
        log_repository=log_repository,
        channel_factory=FakeMixedChannelFactory(),
        session=session,
    )
    logs = await service.create_pending_delivery_logs(
        category_id=1,
        message="Final score alert",
    )

    await service.deliver_pending_logs(log_ids=[log.id for log in logs])

    assert len(log_repository.status_updates) == 3
    assert [update["status"] for update in log_repository.status_updates] == [
        LogStatus.SUCCESS,
        LogStatus.SUCCESS,
        LogStatus.FAILED,
    ]
    assert "simulated" in str(log_repository.status_updates[2]["error_message"]).lower()
    assert session.commits == 1
    assert session.rollbacks == 0


@pytest.mark.asyncio
async def test_notification_service_delivers_batch_concurrently() -> None:
    log_repository = FakeLogRepository()
    session = FakeSession()
    channel_factory = FakeConcurrentChannelFactory()
    service = make_service(
        log_repository=log_repository,
        channel_factory=channel_factory,
        session=session,
    )
    logs = await service.create_pending_delivery_logs(
        category_id=1,
        message="Final score alert",
    )

    await service.deliver_pending_logs(log_ids=[log.id for log in logs])

    assert channel_factory.strategy.max_in_flight > 1
    assert {update["status"] for update in log_repository.status_updates} == {
        LogStatus.SUCCESS
    }
    assert session.commits == 1
    assert session.rollbacks == 0


@pytest.mark.asyncio
async def test_notification_service_rejects_unknown_category() -> None:
    service = make_service(
        category_repository=FakeCategoryRepository(exists=False),
        channel_factory=FakeSuccessChannelFactory(),
    )

    with pytest.raises(CategoryNotFoundError):
        await service.create_pending_delivery_logs(
            category_id=999,
            message="Unknown category",
        )
