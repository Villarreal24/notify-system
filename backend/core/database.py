from collections.abc import AsyncIterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import get_settings


settings = get_settings()

engine_kwargs: dict = {
    "echo": False,
    "pool_pre_ping": True,
    "pool_size": settings.db_pool_size,
    "max_overflow": settings.db_max_overflow,
    "pool_timeout": settings.db_pool_timeout,
}
engine = create_async_engine(settings.database_url, **engine_kwargs)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


@event.listens_for(engine.sync_engine, "connect")
def _on_connect_set_statement_timeout(
    dbapi_connection: object,
    _connection_record: object,
) -> None:
    if settings.db_statement_timeout_ms <= 0:
        return
    # Raw DBAPI: integer GUC, avoid driver-specific parameter styles for asyncpg/psycopg.
    timeout_ms = int(settings.db_statement_timeout_ms)
    cursor = dbapi_connection.cursor()  # type: ignore[union-attr]
    try:
        cursor.execute(f"SET statement_timeout = {timeout_ms}")
    finally:
        cursor.close()


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session
