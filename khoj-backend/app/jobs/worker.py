"""Infrastructure health task only; later phases register domain jobs explicitly."""

from collections.abc import Awaitable, Callable
from typing import Any, ClassVar

from arq import cron
from arq.connections import RedisSettings

from app.config import get_settings
from app.jobs.intake import dispatch_intake_matches


async def dependency_health(ctx: dict[str, Any]) -> bool:
    return bool(await ctx["redis"].ping())


class WorkerSettings:
    # arq requires at least one registered function, including for an idle B0 worker.
    functions: ClassVar[list[Callable[..., Awaitable[bool]]]] = [
        dependency_health,
        dispatch_intake_matches,
    ]
    cron_jobs = [cron(dispatch_intake_matches, second={0, 30}, run_at_startup=True)]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    health_check_interval = 30
