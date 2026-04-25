from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Channel


class ChannelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[Channel]:
        result = await self.session.scalars(select(Channel).order_by(Channel.id))
        return list(result)
