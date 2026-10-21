import hashlib
import math
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from redis.asyncio import Redis

# Atomic sliding-window log on a sorted set (score = timestamp in ms).
# KEYS[1] - zset key
# ARGV    - now_ms, window_ms, limit, unique member
# Window is (now - window, now]: entries with score <= now - window are expired.
# Returns {allowed (0/1), remaining, retry_after_ms}
SLIDING_WINDOW_LUA = """
local key    = KEYS[1]
local now    = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit  = tonumber(ARGV[3])

redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
local count = redis.call('ZCARD', key)

if count < limit then
    redis.call('ZADD', key, now, ARGV[4])
    redis.call('PEXPIRE', key, window)
    return {1, limit - count - 1, 0}
end

local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
local retry_ms = tonumber(oldest[2]) + window - now
return {0, 0, retry_ms}
"""


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int  # whole seconds, >= 1 when not allowed, 0 otherwise


class SlidingWindowRateLimiter:
    def __init__(
        self,
        redis: Redis,
        limit: int,
        window_seconds: float,
        clock: Callable[[], float] = time.time,
        prefix: str = "ratelimit",
    ) -> None:
        self._limit = limit
        self._window_ms = int(window_seconds * 1000)
        self._clock = clock
        self._prefix = prefix
        self._script = redis.register_script(SLIDING_WINDOW_LUA)

    def _key(self, api_key: str) -> str:
        # Hash so raw API keys never end up in Redis.
        return f"{self._prefix}:{hashlib.sha256(api_key.encode()).hexdigest()}"

    async def check(self, api_key: str) -> RateLimitResult:
        now_ms = round(self._clock() * 1000)
        allowed, remaining, retry_ms = await self._script(
            keys=[self._key(api_key)],
            args=[now_ms, self._window_ms, self._limit, uuid.uuid4().hex],
        )
        retry_after = 0 if allowed else max(1, math.ceil(retry_ms / 1000))
        return RateLimitResult(bool(allowed), self._limit, int(remaining), retry_after)
