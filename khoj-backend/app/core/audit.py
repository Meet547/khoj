from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import AuditLog


@dataclass(frozen=True)
class Actor:
    id: UUID | None
    role: str = "citizen"


def audit(db: AsyncSession, actor: Actor, action: str, person_id: UUID) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id,
            actor_role=actor.role,
            action=action,
            object_type="person",
            object_id=str(person_id),
            meta={},
        )
    )


async def audit_read(
    factory: async_sessionmaker[AsyncSession], actor: Actor, action: str, person_ids: list[UUID]
) -> None:
    # A read event must survive a caller's later transaction rollback or denied response.
    async with factory() as db, db.begin():
        for person_id in person_ids:
            audit(db, actor, action, person_id)
