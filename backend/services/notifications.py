import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from tenacity import retry, stop_after_attempt, wait_fixed

from models import LogStatus, NotificationLog, User
from repositories.categories import CategoryRepository
from repositories.logs import NotificationLogRepository
from repositories.users import UserRepository
from strategies.notification_channel import NotificationChannel, SendResult
from strategies.factory import ChannelFactory

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class CategoryNotFoundError(ValueError):
    pass


class NotificationDeliveryError(RuntimeError):
    pass


@dataclass(frozen=True)
class DeliverySummary:
    recipients: int
    deliveries: int


@dataclass(frozen=True)
class DeliveryAttempt:
    log: NotificationLog
    result: SendResult


class NotificationService:
    def __init__(
        self,
        *,
        category_repository: CategoryRepository,
        user_repository: UserRepository,
        log_repository: NotificationLogRepository,
        channel_factory: ChannelFactory,
        session: "AsyncSession | None" = None,
    ) -> None:
        self.category_repository = category_repository
        self.user_repository = user_repository
        self.log_repository = log_repository
        self.channel_factory = channel_factory
        self.session = session

    async def ensure_category_exists(self, category_id: int) -> None:
        category = await self.category_repository.get_by_id(category_id)
        if category is None:
            raise CategoryNotFoundError(f"Category {category_id} does not exist")

    async def commit(self) -> None:
        if self.session is not None:
            await self.session.commit()

    async def rollback(self) -> None:
        if self.session is not None:
            await self.session.rollback()

    async def create_pending_delivery_logs(
        self, *, category_id: int, message: str
    ) -> list[NotificationLog]:
        category = await self.category_repository.get_by_id(category_id)
        if category is None:
            raise CategoryNotFoundError(f"Category {category_id} does not exist")

        users = await self.user_repository.list_by_category(category_id)
        logs: list[NotificationLog] = []

        for user in users:
            for channel in user.channels:
                log = await self.log_repository.create(
                    message=message,
                    category_id=category_id,
                    channel_id=channel.id,
                    user_id=user.id,
                )
                log.category = category
                log.channel = channel
                log.user = user
                logs.append(log)

        return logs

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)
    async def _send_with_retry(
        self, *, strategy: NotificationChannel, user: User, message: str
    ) -> SendResult:
        result = await strategy.send(user=user, message=message)
        if not result.delivered:
            raise NotificationDeliveryError(result.detail)
        return result

    async def deliver(self, *, category_id: int, message: str) -> DeliverySummary:
        await self.ensure_category_exists(category_id)
        users = await self.user_repository.list_by_category(category_id)
        deliveries = 0

        for user in users:
            for channel in user.channels:
                strategy = self.channel_factory.get(channel.name)
                await self._send_with_retry(strategy=strategy, user=user, message=message)
                deliveries += 1

        return DeliverySummary(recipients=len(users), deliveries=deliveries)

    async def _send_delivery_log(
        self, *, log: NotificationLog, semaphore: asyncio.Semaphore
    ) -> DeliveryAttempt:
        async with semaphore:
            if log.user is None or log.channel is None:
                raise NotificationDeliveryError("Delivery log is missing user or channel")

            strategy = self.channel_factory.get(log.channel.name)
            result = await self._send_with_retry(
                strategy=strategy,
                user=log.user,
                message=log.message,
            )
            return DeliveryAttempt(log=log, result=result)

    async def deliver_pending_logs(self, *, log_ids: list[UUID]) -> None:
        logs = [
            log
            for log_id in log_ids
            if (log := await self.log_repository.get_by_id(log_id)) is not None
        ]
        semaphore = asyncio.Semaphore(50)
        tasks = [
            self._send_delivery_log(log=log, semaphore=semaphore)
            for log in logs
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        try:
            for log, result in zip(logs, results, strict=True):
                if isinstance(result, Exception):
                    await self.log_repository.update_status(
                        log_id=log.id,
                        status=LogStatus.FAILED,
                        error_message=str(result),
                    )
                else:
                    await self.log_repository.update_status(
                        log_id=result.log.id,
                        status=LogStatus.SUCCESS,
                        error_message=None,
                    )

            await self.commit()
        except Exception:
            await self.rollback()
            raise

    async def deliver_pending_log(self, *, log_id: UUID) -> NotificationLog | None:
        log = await self.log_repository.get_by_id(log_id)
        if log is None:
            return None

        try:
            if log.user is None or log.channel is None:
                raise NotificationDeliveryError("Delivery log is missing user or channel")

            strategy = self.channel_factory.get(log.channel.name)
            await self._send_with_retry(
                strategy=strategy,
                user=log.user,
                message=log.message,
            )
            await self.log_repository.update_status(
                log_id=log_id,
                status=LogStatus.SUCCESS,
                error_message=None,
            )
            await self.commit()
            return log
        except Exception as exc:
            await self.rollback()
            await self.log_repository.update_status(
                log_id=log_id,
                status=LogStatus.FAILED,
                error_message=str(exc),
            )
            await self.commit()
            return None
