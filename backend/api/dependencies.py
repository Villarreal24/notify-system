from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from repositories.categories import CategoryRepository
from repositories.channels import ChannelRepository
from repositories.logs import NotificationLogRepository
from repositories.users import UserRepository
from services.catalog import CatalogService
from services.logs import LogService
from services.notifications import NotificationService
from strategies.factory import ChannelFactory


async def get_catalog_service(
    session: AsyncSession = Depends(get_session),
) -> AsyncIterator[CatalogService]:
    yield CatalogService(
        category_repository=CategoryRepository(session),
        channel_repository=ChannelRepository(session),
    )


async def get_log_service(
    session: AsyncSession = Depends(get_session),
) -> AsyncIterator[LogService]:
    yield LogService(log_repository=NotificationLogRepository(session))


async def get_notification_service(
    session: AsyncSession = Depends(get_session),
) -> AsyncIterator[NotificationService]:
    yield NotificationService(
        category_repository=CategoryRepository(session),
        user_repository=UserRepository(session),
        log_repository=NotificationLogRepository(session),
        channel_factory=ChannelFactory(),
        session=session,
    )
