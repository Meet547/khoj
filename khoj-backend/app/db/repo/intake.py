"""Owner-scoped intake persistence. No graph text can invoke arbitrary writes."""

import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from text_unidecode import unidecode

from app.core.audit import Actor, audit
from app.core.errors import AppError
from app.core.ids import next_case_number
from app.db.models import (
    CaseEvent,
    Consent,
    IntakeMatchJob,
    IntakeSession,
    Person,
    PersonName,
    Photo,
    Report,
    Watche,
)


def name_variants(value: str, original: str) -> set[str]:
    variants = {
        value.strip(),
        original.strip(),
        unidecode(original).strip(),
        unidecode(value).strip(),
    }
    aliases = {"mohd", "mohammad", "muhammad", "mohammed"}
    for name in list(variants):
        words = name.split()
        if words and words[0].casefold().rstrip(".") in aliases:
            variants.update(" ".join([alias.capitalize(), *words[1:]]) for alias in aliases)
    return {v for v in variants if v and len(v) <= 120}


class IntakeRepository:
    def __init__(self, factory: async_sessionmaker[AsyncSession]):
        self.factory = factory

    async def persist(self, state: dict[str, Any]) -> dict[str, str]:
        owner = UUID(state["owner_id"])
        sid = UUID(state["session_id"])
        async with self.factory() as db, db.begin():
            session = await db.get(IntakeSession, sid, with_for_update=True)
            if session is None or (session.user_id is not None and session.user_id != owner):
                raise AppError("forbidden", "This session is unavailable.", 403)
            existing = await db.scalar(select(Report).where(Report.session_id == sid))
            if existing:
                if existing.owner_id != owner:
                    raise AppError("forbidden", "This session is unavailable.", 403)
                return {"case_no": existing.case_no, "person_id": str(existing.person_id)}
            if (
                not state.get("consent")
                or state.get("stage") != "confirmed"
                or state.get("conflicts")
            ):
                raise AppError("confirmation_required", "Please confirm the reviewed details.", 409)
            draft = state["draft"]
            values = {key: field["value"] for key, field in draft.items()}
            age = re.fullmatch(
                r"(\d{1,3})(?:\s*(?:years?(?: old)?|yrs?))?", values.get("age", ""), re.I
            )
            age_num = int(age[1]) if age and int(age[1]) <= 120 else None
            person = Person(
                origin="khoj",
                kind=session.kind,
                access_class="restricted",
                name_original=values.get("name"),
                gender=values.get("gender"),
                age_min=age_num,
                age_max=age_num,
                marks_text=values.get("marks"),
                clothing_text=values.get("clothing"),
                place_text=values.get("last_seen_place"),
                build=values.get("build"),
                complexion=values.get("complexion"),
                hair=values.get("hair"),
                language=[values["language"]] if values.get("language") else [],
                conditions=[values["conditions"]] if values.get("conditions") else [],
                attrs={"draft": draft},
            )
            # The canonical person writer remains in the person repository boundary.
            from app.db.repo.persons import PersonRepository

            actor = Actor(owner, state.get("owner_role", "citizen"))
            await PersonRepository(db, self.factory, actor).create_intake(person, session, owner)
            if "name" in draft:
                for variant in name_variants(values["name"], draft["name"]["evidence"]):
                    db.add(
                        PersonName(
                            person_id=person.id,
                            name=variant,
                            script="original" if not variant.isascii() else "Latin",
                            phonetic=unidecode(variant).casefold(),
                        )
                    )
            for photo_id in state["photo_ids"]:
                photo = await db.get(Photo, UUID(photo_id), with_for_update=True)
                if photo is None or photo.session_id != sid or photo.person_id is not None:
                    raise AppError("invalid_photo", "A photo is unavailable for this session.", 409)
                photo.person_id = person.id
            report = Report(
                case_no=await next_case_number(db),
                person_id=person.id,
                owner_id=owner,
                session_id=sid,
                relation=values.get("relation"),
                consent={"confirmed": True, "version": "intake-v1"},
            )
            db.add(report)
            await db.flush()
            db.add_all(
                [
                    Watche(report_id=report.id),
                    CaseEvent(
                        report_id=report.id,
                        kind="report_filed",
                        text_key="report_filed",
                        params={"case_no": report.case_no},
                    ),
                    IntakeMatchJob(person_id=person.id, report_id=report.id),
                    Consent(
                        user_id=owner, purpose="intake", text_version="intake-v1", granted=True
                    ),
                ]
            )
            session.user_id, session.status = owner, "saved"
            session.guest_token_hash = None
            session.updated_at = datetime.now(UTC)
            audit(db, actor, "file_report", person.id)
            await db.flush()
            return {"case_no": report.case_no, "person_id": str(person.id)}
