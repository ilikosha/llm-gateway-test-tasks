"""Тесты идут против настоящего PostgreSQL.

TEST_DATABASE_URL задан  -> используется он (например, db из docker compose);
не задан                 -> поднимается одноразовый контейнер через testcontainers.
"""

import os

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text

from jobqueue.api import create_app
from jobqueue.config import Settings
from helpers import WORKER_TOKENS
from jobqueue.db import make_engine
from jobqueue.migrate import upgrade


@pytest.fixture(scope="session")
def database_url():
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        upgrade(url)
        yield url
        return
    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as pg:
        url = pg.get_connection_url()
        upgrade(url)  # схема только через Alembic-миграции
        yield url


@pytest_asyncio.fixture
async def engine(database_url):
    engine = make_engine(database_url)
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE jobs"))
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def client(engine):
    # ASGITransport не запускает lifespan; миграции применены фикстурой database_url.
    app = create_app(Settings(reaper_enabled=False, worker_tokens=WORKER_TOKENS), engine=engine)
    app.state.engine = engine
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
