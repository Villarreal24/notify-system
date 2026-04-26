"""
Idempotent seed for catalog data and sample users. Run after migrations:

    cd backend && .venv/bin/python -m seed_data
"""

import asyncio
import os
import sys
from typing import cast
from uuid import UUID

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import Table, func, insert, select, text

from core.database import async_session_factory
from models import Category, Channel, User
from models.entities import user_channels, user_subscriptions


CATEGORY_SEEDS = ((1, "Sports"), (2, "Finance"), (3, "Movies"))
CHANNEL_SEEDS = ((1, "SMS"), (2, "E-Mail"), (3, "Push Notification"))
USER_SEEDS: tuple[
    tuple[UUID, str, str, str, list[int], list[int]], ...
] = (
    (
        UUID("a1b2c3d4-0000-0000-0000-000000000001"),
        "Alice Johnson",
        "alice@example.com",
        "+1234567890",
        [1, 3],
        [2],
    ),
    (
        UUID("a1b2c3d4-0000-0000-0000-000000000002"),
        "Bob Smith",
        "bob@example.com",
        "+1987654321",
        [2],
        [1],
    ),
    (
        UUID("a1b2c3d4-0000-0000-0000-000000000003"),
        "Charlie Brown",
        "charlie@example.com",
        "+1122334455",
        [1, 2, 3],
        [2, 3],
    ),
)


async def _ensure_catalog_row(
    model: type[Category] | type[Channel],
    rows: tuple[tuple[int, str], ...],
) -> None:
    async with async_session_factory() as session:
        for row_id, name in rows:
            result = await session.get(model, row_id)
            if result is None:
                session.add(model(id=row_id, name=name))  # type: ignore[call-arg]
        max_id = await session.scalar(select(func.max(model.id)))
        m = 0 if max_id is None else int(max_id)
        table = cast(Table, model.__table__)
        await session.execute(
            text("SELECT setval(pg_get_serial_sequence(:tbl, 'id'), :m, true)").bindparams(
                tbl=table.fullname, m=m
            )
        )
        await session.commit()


async def _ensure_users() -> None:
    async with async_session_factory() as session:
        for user_id, name, email, phone, _subs, _ch in USER_SEEDS:
            result = await session.get(User, user_id)
            if result is None:
                session.add(
                    User(  # type: ignore[call-arg]
                        id=user_id,
                        name=name,
                        email=email,
                        phone_number=phone,
                        deleted_at=None,
                    )
                )
        await session.commit()


async def _ensure_subscriptions() -> None:
    async with async_session_factory() as session:
        for user_id, _name, _e, _p, category_ids, channel_ids in USER_SEEDS:
            user = await session.get(User, user_id)
            if user is None:
                continue
            for cid in category_ids:
                count = await session.scalar(
                    select(func.count())
                    .select_from(user_subscriptions)
                    .where(
                        user_subscriptions.c.user_id == user_id,
                        user_subscriptions.c.category_id == cid,
                    )
                )
                if not count:
                    await session.execute(
                        insert(user_subscriptions).values(
                            user_id=user_id, category_id=cid
                        )
                    )
            for chid in channel_ids:
                count = await session.scalar(
                    select(func.count())
                    .select_from(user_channels)
                    .where(
                        user_channels.c.user_id == user_id,
                        user_channels.c.channel_id == chid,
                    )
                )
                if not count:
                    await session.execute(
                        insert(user_channels).values(
                            user_id=user_id, channel_id=chid
                        )
                    )
        await session.commit()


async def main() -> None:
    await _ensure_catalog_row(Category, CATEGORY_SEEDS)
    await _ensure_catalog_row(Channel, CHANNEL_SEEDS)
    await _ensure_users()
    await _ensure_subscriptions()


if __name__ == "__main__":
    asyncio.run(main())
