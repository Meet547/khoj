"""Idempotent demo seed; never seeds privileged accounts outside demo mode."""

import asyncio

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.auth import DEMO_ROLES
from app.config import get_settings
from app.core.security import PhoneVault
from app.db.models import GazetteerPlace, ScoringVersion, User


async def seed() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, hide_parameters=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as db, db.begin():
            if settings.demo_auth:
                vault = PhoneVault(settings)
                for phone, role in DEMO_ROLES.items():
                    await db.execute(
                        insert(User)
                        .values(
                            phone_hash=vault.digest(phone),
                            phone_enc=vault.encrypt(phone),
                            role=role,
                            lang="hi",
                        )
                        .on_conflict_do_nothing(index_elements=[User.phone_hash])
                    )
            if await db.scalar(select(ScoringVersion.id).limit(1)) is None:
                # Not calibrated; matching/notifications are not implemented at B0.
                db.add(ScoringVersion(weights={"placeholder": True}, active=True))
            if await db.scalar(select(GazetteerPlace.id).limit(1)) is None:
                db.add(
                    GazetteerPlace(
                        name="New Delhi",
                        name_hi="नई दिल्ली",
                        kind="city",
                        state="Delhi",
                        district="New Delhi",
                        lat=28.6139,
                        lng=77.2090,
                    )
                )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
