"""Retry the transactional match outbox. B3 consumes the separate khoj:matching queue."""

from datetime import UTC, datetime
from typing import Any

from arq.connections import ArqRedis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models import IntakeMatchJob


async def dispatch_intake_matches(ctx: dict[str, Any]) -> bool:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, hide_parameters=True)
    try:
        async with async_sessionmaker(engine)() as db, db.begin():
            jobs = list(
                (
                    await db.scalars(
                        select(IntakeMatchJob)
                        .where(IntakeMatchJob.enqueued_at.is_(None))
                        .limit(100)
                        .with_for_update(skip_locked=True)
                    )
                ).all()
            )
            queue: ArqRedis = ctx["redis"]
            for job in jobs:
                await queue.enqueue_job(
                    "match_new_record",
                    str(job.person_id),
                    _job_id=f"intake:{job.person_id}",
                    _queue_name="khoj:matching",
                )
                job.enqueued_at = datetime.now(UTC)
        return True
    finally:
        await engine.dispose()
