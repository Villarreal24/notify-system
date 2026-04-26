from models import NotificationLog
from repositories.logs import NotificationLogRepository
from schemas.notifications import NotificationLogRead


class LogService:
    def __init__(self, log_repository: NotificationLogRepository) -> None:
        self.log_repository = log_repository

    async def list_recent(self, limit: int = 50) -> list[NotificationLogRead]:
        logs = await self.log_repository.list_recent(limit=limit)
        return [notification_log_to_read_model(log) for log in logs]


def notification_log_to_read_model(log: NotificationLog) -> NotificationLogRead:
    return NotificationLogRead(
        id=log.id,
        message=log.message,
        category_id=log.category_id,
        category_name=log.category.name if log.category else None,
        channel_id=log.channel_id,
        channel_name=log.channel.name if log.channel else None,
        user_id=log.user_id,
        user_name=log.user.name if log.user else None,
        status=log.status,
        error_message=log.error_message,
        created_at=log.created_at,
    )
