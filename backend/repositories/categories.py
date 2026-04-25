from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Category


class CategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[Category]:
        result = await self.session.scalars(select(Category).order_by(Category.id))
        return list(result)

    async def get_by_id(self, category_id: int) -> Category | None:
        return await self.session.get(Category, category_id)
