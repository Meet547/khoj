"""Atomic daily provider-attempt accounting, shared across workers (UTC days)."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, cast

from redis.asyncio import Redis

from app.core.rate_limit import eval_script

RESERVE = """
local calls = tonumber(redis.call('HGET', KEYS[1], 'calls') or '0')
local tokens = tonumber(redis.call('HGET', KEYS[1], 'tokens') or '0')
local hit = (tonumber(ARGV[1]) >= 0 and calls >= tonumber(ARGV[1])) or
            (tonumber(ARGV[2]) >= 0 and tokens >= tonumber(ARGV[2]))
if hit and ARGV[3] == '1' then return 0 end
redis.call('HINCRBY', KEYS[1], 'calls', 1)
redis.call('EXPIRE', KEYS[1], 172800)
return 1
"""
TOKENS = """
redis.call('HINCRBY', KEYS[1], 'tokens', ARGV[1])
redis.call('EXPIRE', KEYS[1], 172800)
return 1
"""


class BudgetExceeded(Exception):
    pass


class Usage:
    def __init__(self, redis: Redis, cfg: dict[str, Any]):
        self.redis, self.cfg = redis, cfg

    def key(self, role: str, day: str) -> str:
        return f"llm:usage:{day}:{role}"

    def day(self) -> str:
        return datetime.now(UTC).date().isoformat()

    def limits(self, role: str) -> dict[str, int]:
        return dict(self.cfg["roles"][role].get("budget", {}))

    async def reserve(self, role: str) -> str:
        day = self.day()
        limits = self.limits(role)
        allowed = await eval_script(
            self.redis,
            RESERVE,
            1,
            self.key(role, day),
            limits.get("calls", -1),
            limits.get("tokens", -1),
            int(role in {"compare", "explain"}),
        )
        if not allowed:
            raise BudgetExceeded(role)
        return day

    async def tokens(self, role: str, day: str, data: dict[str, Any]) -> None:
        total = sum(max(0, int(data.get(k) or 0)) for k in ("prompt_eval_count", "eval_count"))
        await eval_script(self.redis, TOKENS, 1, self.key(role, day), total)

    async def snapshot(self) -> dict[str, Any]:
        day = self.day()
        roles = {}
        for role, cfg in self.cfg["roles"].items():
            get_all = cast(Callable[[str], Awaitable[dict[Any, Any]]], self.redis.hgetall)
            raw = await get_all(self.key(role, day))
            values = {(k.decode() if isinstance(k, bytes) else k): int(v) for k, v in raw.items()}
            counts = {"calls": values.get("calls", 0), "tokens": values.get("tokens", 0)}
            limits = self.limits(role)
            hit = any(counts[k] >= v for k, v in limits.items() if v >= 0)
            roles[role] = {
                **counts,
                "limits": limits,
                "thresholdHit": hit,
                "disabled": not cfg.get("enabled", True)
                or (hit and role in {"compare", "explain"}),
            }
        return {"day": day, "timezone": "UTC", "roles": roles}
