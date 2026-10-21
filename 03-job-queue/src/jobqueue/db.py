from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def make_engine(url: str) -> AsyncEngine:
    return create_async_engine(
        url, pool_size=20, max_overflow=30, pool_pre_ping=True, pool_timeout=5
    )
