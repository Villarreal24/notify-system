from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import LogStatus, NotificationLog


class NotificationLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_recent(self, limit: int = 50) -> list[NotificationLog]:
        statement = (
            select(NotificationLog)
            .options(
                selectinload(NotificationLog.category),
                selectinload(NotificationLog.channel),
                selectinload(NotificationLog.user),
            )
            .order_by(NotificationLog.created_at.desc())
            .limit(limit)
        )
        result = await self.session.scalars(statement)
        return list(result)

    async def get_by_id(self, log_id: UUID) -> NotificationLog | None:
        statement = (
            select(NotificationLog)
            .options(
                selectinload(NotificationLog.category),
                selectinload(NotificationLog.channel),
                selectinload(NotificationLog.user),
            )
            .where(NotificationLog.id == log_id)
        )
        result = await self.session.scalars(statement)
        return result.first()

    async def create(
        self,
        *,
        message: str,
        category_id: int,
        channel_id: int | None = None,
        user_id: UUID | None = None,
    ) -> NotificationLog:
        log = NotificationLog(
            message=message,
            category_id=category_id,
            channel_id=channel_id,
            user_id=user_id,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def update_status(
        self,
        *,
        log_id: UUID,
        status: LogStatus,
        error_message: str | None = None,
    ) -> NotificationLog | None:
        log = await self.session.get(NotificationLog, log_id)
        if log is None:
            return None

        log.status = status
        log.error_message = error_message
        await self.session.flush()
        return log
