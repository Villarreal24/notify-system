from models import Category, Channel
from repositories.categories import CategoryRepository
from repositories.channels import ChannelRepository


class CatalogService:
    def __init__(
        self,
        category_repository: CategoryRepository,
        channel_repository: ChannelRepository,
    ) -> None:
        self.category_repository = category_repository
        self.channel_repository = channel_repository

    async def list_categories(self) -> list[Category]:
        return await self.category_repository.list_all()

    async def list_channels(self) -> list[Channel]:
        return await self.channel_repository.list_all()
