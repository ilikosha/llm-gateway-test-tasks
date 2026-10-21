import asyncio

from sqlalchemy import text

from jobqueue.migrate import upgrade


async def test_schema_comes_from_migrations(engine, database_url):
    await asyncio.to_thread(upgrade, database_url)  # повторный запуск идемпотентен
    async with engine.connect() as conn:
        version = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar()
        indexes = {r[0]: r[1] for r in await conn.execute(
            text("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'jobs'"))}
    assert version == "0001"
    assert "WHERE (status = 'queued'::text)" in indexes["jobs_queued_idx"]
    assert "WHERE (status = 'running'::text)" in indexes["jobs_running_idx"]


async def test_status_check_constraint(engine):
    import pytest
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        async with engine.begin() as conn:
            await conn.execute(text("INSERT INTO jobs (prompt, status) VALUES ('x', 'bogus')"))
