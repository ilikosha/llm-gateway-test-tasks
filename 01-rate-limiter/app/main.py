import hmac
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Response
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import Settings
from app.limiter import RateLimitResult, SlidingWindowRateLimiter


def _rate_limit_headers(result: RateLimitResult) -> dict[str, str]:
    headers = {
        "X-RateLimit-Limit": str(result.limit),
        "X-RateLimit-Remaining": str(result.remaining),
    }
    if not result.allowed:
        headers["Retry-After"] = str(result.retry_after)
    return headers


def create_app(
    settings: Settings | None = None,
    redis: Redis | None = None,
    clock: Callable[[], float] = time.time,
) -> FastAPI:
    settings = settings or Settings()
    redis = redis or Redis.from_url(settings.redis_url)
    limiter = SlidingWindowRateLimiter(
        redis, settings.rate_limit_requests, settings.rate_limit_window_seconds, clock
    )
    allowed_keys = settings.api_keys_set
    if not allowed_keys:
        raise RuntimeError("API_KEYS must contain at least one key")

    def _is_known(token: str) -> bool:
        # Constant-time comparison against every key, no early exit.
        presented = token.encode()
        found = False
        for key in allowed_keys:
            found |= hmac.compare_digest(presented, key.encode())
        return found

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await redis.aclose()

    app = FastAPI(title="Rate-limited echo", lifespan=lifespan)

    async def authenticate(authorization: Annotated[str | None, Header()] = None) -> str:
        scheme, _, token = (authorization or "").partition(" ")
        token = token.strip()
        if scheme.lower() != "bearer" or not token or not _is_known(token):
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return token

    async def rate_limit(
        response: Response, api_key: Annotated[str, Depends(authenticate)]
    ) -> None:
        try:
            result = await limiter.check(api_key)
        except RedisError as exc:
            raise HTTPException(status_code=503, detail="Rate limiter unavailable") from exc
        headers = _rate_limit_headers(result)
        if not result.allowed:
            raise HTTPException(status_code=429, detail="Rate limit exceeded", headers=headers)
        response.headers.update(headers)

    @app.post("/v1/echo", dependencies=[Depends(rate_limit)])
    async def echo(body: Annotated[Any, Body()]) -> Any:
        return body

    return app
