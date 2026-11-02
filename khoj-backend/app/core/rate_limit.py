from collections.abc import Awaitable, Callable
from typing import Any, cast

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.errors import AppError

# INCR + EXPIRE must be atomic, including for requests on separate API instances.
WINDOW = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return {count, redis.call('TTL', KEYS[1])}
"""
CHALLENGE = """
if redis.call('EXISTS', KEYS[1]) == 0 then return 0 end
redis.call('DEL', KEYS[1])
return 1
"""


async def eval_script(redis: Redis, script: str, keys: int, *args: str | int) -> Any:
    # redis-py's shared sync/async command stubs require narrowing at this boundary.
    evaluate = cast(Callable[..., Awaitable[Any]], redis.eval)
    return await evaluate(script, keys, *args)


class RateLimiter:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def check(self, key: str, limit: int, window: int = 3600) -> None:
        try:
            count, remaining = await eval_script(self.redis, WINDOW, 1, "rate:" + key, window)
        except RedisError as exc:
            raise AppError(
                "temporarily_unavailable", "Please try again in a moment.", 503, retryable=True
            ) from exc
        if int(count) > limit:
            raise AppError(
                "rate_limited",
                "Too many attempts. Please try again later.",
                429,
                retryable=True,
                retry_after=max(1, int(remaining)),
            )
