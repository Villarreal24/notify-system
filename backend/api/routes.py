import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from api.dependencies import (
    get_catalog_service,
    get_log_service,
    get_notification_service,
)
from core.database import async_session_factory, get_session
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.categories import CategoryRepository
from repositories.logs import NotificationLogRepository
from repositories.users import UserRepository
from schemas.catalog import CategoryRead, ChannelRead
from schemas.notifications import NotificationCreate, NotificationLogRead
from services.catalog import CatalogService
from services.logs import LogService, notification_log_to_read_model
from services.notifications import NotificationService
from strategies.factory import ChannelFactory

router = APIRouter()
logger = logging.getLogger(__name__)


async def deliver_notification_background(log_ids: list[UUID]) -> None:
    async with async_session_factory() as session:
        service = NotificationService(
            category_repository=CategoryRepository(session),
            user_repository=UserRepository(session),
            log_repository=NotificationLogRepository(session),
            channel_factory=ChannelFactory(),
            session=session,
        )
        try:
            await service.deliver_pending_logs(log_ids=log_ids)
        except Exception:
            await session.rollback()
            logger.exception("Background notification delivery failed")


@router.get("/health")
async def health(
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@router.get("/categories", response_model=list[CategoryRead])
async def list_categories(
    service: CatalogService = Depends(get_catalog_service),
) -> list[CategoryRead]:
    categories = await service.list_categories()
    return [CategoryRead.model_validate(category) for category in categories]


@router.get("/channels", response_model=list[ChannelRead])
async def list_channels(
    service: CatalogService = Depends(get_catalog_service),
) -> list[ChannelRead]:
    channels = await service.list_channels()
    return [ChannelRead.model_validate(channel) for channel in channels]


@router.get("/notification-logs", response_model=list[NotificationLogRead])
async def list_notification_logs(
    limit: int = Query(default=50, ge=1, le=100),
    service: LogService = Depends(get_log_service),
) -> list[NotificationLogRead]:
    return await service.list_recent(limit=limit)


@router.post(
    "/notifications",
    response_model=list[NotificationLogRead],
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_notification(
    payload: NotificationCreate,
    background_tasks: BackgroundTasks,
    service: NotificationService = Depends(get_notification_service),
) -> list[NotificationLogRead]:
    try:
        logs = await service.create_pending_delivery_logs(
            category_id=payload.category_id,
            message=payload.message,
        )
        await service.commit()
    except Exception:
        await service.rollback()
        raise

    log_ids = [log.id for log in logs]
    if log_ids:
        background_tasks.add_task(deliver_notification_background, log_ids)

    return [notification_log_to_read_model(log) for log in logs]
