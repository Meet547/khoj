"""All canonical person access goes through policy filters and audit hooks here."""

from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.audit import Actor, audit, audit_read
from app.core.errors import AppError
from app.db.models import IntakeSession, Person


class PersonRepository:
    def __init__(
        self, db: AsyncSession, audit_factory: async_sessionmaker[AsyncSession], actor: Actor
    ):
        self.db, self.audit_factory, self.actor = db, audit_factory, actor

    def _visible(self, statement: Select[tuple[Person]]) -> Select[tuple[Person]]:
        if self.actor.role in ("officer", "admin") and self.actor.id is not None:
            return statement
        if self.actor.role == "volunteer" and self.actor.id is not None:
            return statement.where(
                Person.access_class != "officer_only", Person.kind != "unidentified_body"
            )
        return statement.where(Person.access_class == "public_summary", Person.kind == "missing")

    async def get(self, person_id: UUID) -> Person | None:
        person = await self.db.scalar(self._visible(select(Person).where(Person.id == person_id)))
        if person is not None and person.access_class != "public_summary":
            await audit_read(self.audit_factory, self.actor, "read", [person.id])
        return person

    async def list(self, *, limit: int = 50, after: UUID | None = None) -> list[Person]:
        query = self._visible(select(Person)).order_by(Person.id).limit(max(1, min(limit, 200)))
        if after is not None:
            query = query.where(Person.id > after)
        persons = list((await self.db.scalars(query)).all())
        await audit_read(
            self.audit_factory,
            self.actor,
            "read",
            [p.id for p in persons if p.access_class != "public_summary"],
        )
        return persons

    async def create(self, person: Person) -> Person:
        if self.actor.id is None or self.actor.role not in ("officer", "admin"):
            # The B2 owner-scoped intake writer will be a separate, authenticated capability.
            raise AppError("forbidden", "You do not have access to this action.", 403)
        self.db.add(person)
        await self.db.flush()
        if person.access_class != "public_summary":
            audit(self.db, self.actor, "create", person.id)
        return person

    async def create_intake(self, person: Person, session: IntakeSession, owner: UUID) -> Person:
        if self.actor.id != owner or session.user_id not in (None, owner):
            raise AppError("forbidden", "This session is unavailable.", 403)
        if (
            person.origin != "khoj"
            or person.kind != session.kind
            or person.access_class != "restricted"
        ):
            raise AppError("invalid_request", "Invalid intake record.", 422)
        self.db.add(person)
        await self.db.flush()
        audit(self.db, self.actor, "create_intake", person.id)
        return person

    async def set_status(self, person_id: UUID, status: str) -> Person:
        if self.actor.id is None or self.actor.role not in ("officer", "admin"):
            raise AppError("forbidden", "You do not have access to this action.", 403)
        if status not in ("open", "traced", "closed", "source_missing"):
            raise AppError("invalid_status", "Please choose a valid status.", 422)
        person = await self.db.scalar(
            self._visible(select(Person).where(Person.id == person_id).with_for_update())
        )
        if person is None:
            raise AppError("not_found", "This record is unavailable.", 404)
        if person.access_class != "public_summary":
            await audit_read(self.audit_factory, self.actor, "read", [person.id])
            audit(self.db, self.actor, "update_status", person.id)
        person.status = status
        await self.db.flush()
        return person
