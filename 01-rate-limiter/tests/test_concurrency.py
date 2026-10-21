import asyncio

from fakeredis import FakeAsyncRedis

from app.limiter import SlidingWindowRateLimiter


async def test_concurrent_requests_never_exceed_limit():
    limiter = SlidingWindowRateLimiter(FakeAsyncRedis(), limit=10, window_seconds=60, clock=lambda: 1000.0)
    results = await asyncio.gather(*(limiter.check("k") for _ in range(50)))
    assert sum(r.allowed for r in results) == 10
