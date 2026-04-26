from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from uuid import UUID

import pytest

from models import Channel, LogStatus, User
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
        channel_id: int | None = None,
        user_id: UUID | None = None,
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
        FakeSuccessChannelFactory | FakeFailingChannelFactory | FakeMixedChannelFactory | None
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
async def test_notification_service_delivers_to_subscribed_user_channels() -> None:
    log_repository = FakeLogRepository()
    service = make_service(
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
async def test_notification_service_marks_single_delivery_log_success() -> None:
    log_repository = FakeLogRepository()
    session = FakeSession()
    service = make_service(
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
    log.user = cast(
        User,
        SimpleNamespace(
            id=log.user_id,
            email="alice@example.com",
            phone_number="+1234567890",
        ),
    )
    log.channel = cast(Channel, SimpleNamespace(id=2, name="E-Mail"))

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
    service = make_service(
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
    email_log.user = cast(
        User,
        SimpleNamespace(
            id=email_log.user_id,
            email="alice@example.com",
            phone_number="+1234567890",
        ),
    )
    email_log.channel = cast(Channel, SimpleNamespace(id=2, name="E-Mail"))
    push_log = await log_repository.create(
        message="Final score alert",
        category_id=1,
        channel_id=3,
        user_id=UUID("a1b2c3d4-0000-0000-0000-000000000003"),
    )
    push_log.user = cast(
        User,
        SimpleNamespace(
            id=push_log.user_id,
            email="charlie@example.com",
            phone_number="+1122334455",
        ),
    )
    push_log.channel = cast(Channel, SimpleNamespace(id=3, name="Push Notification"))

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
    service = make_service(
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
    log.user = cast(
        User,
        SimpleNamespace(
            id=log.user_id,
            email="alice@example.com",
            phone_number="+1234567890",
        ),
    )
    log.channel = cast(Channel, SimpleNamespace(id=2, name="E-Mail"))

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
    service = make_service(
        category_repository=FakeCategoryRepository(exists=False),
        channel_factory=FakeSuccessChannelFactory(),
    )

    with pytest.raises(CategoryNotFoundError):
        await service.deliver(category_id=999, message="Unknown category")
