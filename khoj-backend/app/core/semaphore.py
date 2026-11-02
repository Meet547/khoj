"""Account-wide STT leases. Redis time avoids clock skew between API instances."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from redis.asyncio import Redis

from app.core.rate_limit import eval_script

ACQUIRE = """
local t = redis.call('TIME')
local now = tonumber(t[1]) + tonumber(t[2]) / 1000000
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then return 0 end
redis.call('ZADD', KEYS[1], now + tonumber(ARGV[2]), ARGV[3])
redis.call('EXPIRE', KEYS[1], ARGV[2])
return 1
"""


class RedisSemaphore:
    def __init__(self, redis: Redis, key: str, slots: int):
        self.redis, self.key, self.slots = redis, key, slots

    @asynccontextmanager
    async def lease(self) -> AsyncIterator[None]:
        token = uuid4().hex
        # Caller bounds acquisition to 8s, and provider work to 270s. A dead worker's
        # lease expires after 300s, safely beyond its maximum HTTP/retry duration.
        while not await eval_script(self.redis, ACQUIRE, 1, self.key, self.slots, 300, token):  # noqa: ASYNC110 -- Redis state spans processes; a local Event cannot signal releases.
            await asyncio.sleep(0.05)
        try:
            yield
        finally:
            await self.redis.zrem(self.key, token)
