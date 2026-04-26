from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import User
from models.entities import user_subscriptions


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_category(self, category_id: int) -> list[User]:
        statement = (
            select(User)
            .join(user_subscriptions, User.id == user_subscriptions.c.user_id)
            .where(
                user_subscriptions.c.category_id == category_id,
                User.deleted_at.is_(None),
            )
            .options(selectinload(User.channels))
            .order_by(User.name)
        )
        result = await self.session.scalars(statement)
        return list(result.unique())
