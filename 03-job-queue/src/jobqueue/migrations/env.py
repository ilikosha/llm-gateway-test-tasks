"""Alembic env (async, asyncpg). URL: config.attributes/ -x / DATABASE_URL."""

import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from jobqueue.config import Settings

config = context.config
# Схема описывается миграциями вручную, autogenerate не используется.
target_metadata = None


def _url() -> str:
    return config.get_main_option("sqlalchemy.url") or Settings().database_url


def _run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        # Advisory-lock: если миграции запустят две реплики сразу, вторая подождёт.
        context.execute("SELECT pg_advisory_xact_lock(727001)")
        context.run_migrations()


async def _run_async() -> None:
    engine = create_async_engine(_url())
    async with engine.connect() as conn:
        await conn.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    context.configure(url=_url(), literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(_run_async())
