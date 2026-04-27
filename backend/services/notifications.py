import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from tenacity import retry, stop_after_attempt, wait_fixed

from models import LogStatus, NotificationLog, User
from core.config import get_settings
from repositories.categories import CategoryRepository
from repositories.logs import NotificationLogRepository
from repositories.users import UserRepository
from strategies.factory import ChannelFactory, UnknownChannelError
from strategies.notification_channel import NotificationChannel, SendResult

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class CategoryNotFoundError(ValueError):
    pass


class NotificationDeliveryError(RuntimeError):
    pass


def _sanitize_notification_failure_message(exc: BaseException) -> str:
    if isinstance(exc, UnknownChannelError):
        return "No delivery strategy is registered for this channel name."
    if isinstance(exc, NotificationDeliveryError):
        return "The channel could not complete delivery for this user."
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return "A transient network or I/O error occurred while delivering the notification."
    if isinstance(exc, RuntimeError):
        return "The channel provider did not complete delivery (simulated or transient error)."
    return "Delivery failed after retries. See server logs for technical details."


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
        settings = get_settings()
        pool_cap = max(1, settings.db_pool_size + settings.db_max_overflow)
        self._max_delivery_concurrency = min(
            max(1, settings.notification_delivery_concurrency),
            pool_cap,
        )

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
        semaphore = asyncio.Semaphore(self._max_delivery_concurrency)
        tasks = [
            self._send_delivery_log(log=log, semaphore=semaphore)
            for log in logs
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        try:
            for log, result in zip(logs, results, strict=True):
                if isinstance(result, DeliveryAttempt):
                    await self.log_repository.update_status(
                        log_id=result.log.id,
                        status=LogStatus.SUCCESS,
                        error_message=None,
                    )
                elif isinstance(result, Exception):
                    await self.log_repository.update_status(
                        log_id=log.id,
                        status=LogStatus.FAILED,
                        error_message=_sanitize_notification_failure_message(result),
                    )
                else:
                    # e.g. KeyboardInterrupt; gather can surface BaseException
                    raise result

            await self.commit()
        except Exception:
            await self.rollback()
            raise
