import asyncio
import hashlib
import hmac
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from arq.connections import ArqRedis
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.core.errors import AppError
from app.db.models import IntakeClip, IntakeMatchJob, IntakeRequest, IntakeSession, Photo, User
from app.graph.engine import IntakeNodes, build_graph
from app.graph.resources import Resources
from app.llm import LLM


class IntakeService:
    def __init__(
        self,
        settings: Settings,
        factory: async_sessionmaker[AsyncSession],
        redis: Redis,
        llm: LLM,
        resources: Resources,
    ):
        self.settings, self.factory, self.redis = settings, factory, redis
        self.resources, self.llm = resources, llm
        self.pool: Any = None
        self.graph: Any = None
        self._init_lock = asyncio.Lock()

    async def ready(self) -> Any:
        if self.graph is None:
            async with self._init_lock:
                if self.graph is None:
                    uri = (
                        make_url(self.settings.database_url)
                        .set(drivername="postgresql")
                        .render_as_string(hide_password=False)
                    )
                    self.pool = AsyncConnectionPool(
                        uri,
                        min_size=1,
                        max_size=5,
                        open=False,
                        kwargs={
                            "autocommit": True,
                            "prepare_threshold": 0,
                            "row_factory": dict_row,
                        },
                    )
                    await self.pool.open()
                    # Tables are installed by Alembic as the migration owner; runtime has no DDL.
                    saver = AsyncPostgresSaver(self.pool)
                    self.graph = build_graph(
                        IntakeNodes(
                            self.llm,
                            self.resources,
                            self.factory,
                            self.enqueue,
                            self.settings.extraction_schema,
                        ),
                        saver,
                    )
        return self.graph

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()

    def config(self, sid: str) -> dict[str, Any]:
        return {"configurable": {"thread_id": sid}, "recursion_limit": 40}

    @asynccontextmanager
    async def locked(
        self, sid: str, token: str | None, user: User | None
    ) -> AsyncIterator[IntakeSession]:
        async with self.factory() as db, db.begin():
            # Serialize graph mutation across workers, including checkpoint updates.
            await db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:id, 0))"), {"id": sid}
            )
            session = await db.get(IntakeSession, UUID(sid))
            token_hash = hashlib.sha256((token or "").encode()).hexdigest()
            permitted = session is not None and (
                (session.user_id is not None and user is not None and session.user_id == user.id)
                or (
                    session.user_id is None
                    and session.guest_token_hash is not None
                    and hmac.compare_digest(session.guest_token_hash, token_hash)
                )
            )
            if not permitted or session is None:
                raise AppError("not_found", "This session is unavailable.", 404)
            self.resources.language(session.lang, production=self.settings.env == "production")
            yield session

    async def create(
        self, kind: str, lang: str, token: str, user: User | None, key: str | None = None
    ) -> str:
        self.resources.language(lang, production=self.settings.env == "production")
        async with self.factory() as db, db.begin():
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            payload = {"kind": kind, "lang": lang}
            if key:
                await db.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:id, 0))"),
                    {"id": f"session:{token_hash}:{key}"},
                )
                old = await db.scalar(
                    select(IntakeRequest)
                    .join(IntakeSession)
                    .where(
                        IntakeSession.guest_token_hash == token_hash,
                        IntakeRequest.key == f"session:{key}",
                    )
                )
                if old:
                    if old.body_hash != self.digest(payload):
                        raise AppError(
                            "idempotency_conflict",
                            "This request key was used with different data.",
                            409,
                        )
                    return str(old.response["sessionId"])
            session = IntakeSession(
                kind=kind,
                lang=lang,
                user_id=user.id if user else None,
                guest_token_hash=token_hash,
            )
            db.add(session)
            await db.flush()
            if key:
                db.add(
                    IntakeRequest(
                        session_id=session.id,
                        key=f"session:{key}",
                        body_hash=self.digest(payload),
                        response={"sessionId": str(session.id)},
                    )
                )
            return str(session.id)

    async def initial(self, session: IntakeSession) -> dict[str, Any]:
        graph = await self.ready()
        snapshot = await graph.aget_state(self.config(str(session.id)))
        if snapshot.values:
            return dict(snapshot.values)
        return {
            "session_id": str(session.id),
            "kind": session.kind,
            "lang": session.lang,
            "draft": {},
            "transcripts": [],
            "asked": [],
            "stage": "collecting",
            "photo_ids": [],
            "conflicts": {},
        }

    async def prior(self, sid: str, key: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        async with self.factory() as db:
            request = await db.get(IntakeRequest, (UUID(sid), key))
            if request is None:
                return None
            if request.body_hash != self.digest(payload):
                raise AppError(
                    "idempotency_conflict", "This request key was used with different data.", 409
                )
            # Renew signed audio URLs at the response layer; persisted replies contain no URLs.
            return request.response

    def digest(self, payload: dict[str, Any]) -> str:
        return hashlib.sha256(
            json.dumps(
                {k: v for k, v in payload.items() if k not in {"stt_ms", "readback"}},
                sort_keys=True,
                ensure_ascii=False,
            ).encode()
        ).hexdigest()

    async def remember(
        self, sid: str, key: str, payload: dict[str, Any], state: dict[str, Any]
    ) -> None:
        async with self.factory() as db, db.begin():
            statement = insert(IntakeRequest).values(
                session_id=UUID(sid), key=key, body_hash=self.digest(payload), response=state
            )
            await db.execute(statement.on_conflict_do_nothing())

    async def run_turn(
        self, session: IntakeSession, payload: dict[str, Any], key: str
    ) -> dict[str, Any]:
        sid = str(session.id)
        previous = await self.prior(sid, key, payload)
        if previous is not None:
            return previous
        graph = await self.ready()
        state = await self.initial(session)
        snapshot = await graph.aget_state(self.config(sid))
        if (
            snapshot.next
            and snapshot.next not in {("confirm",), ("analyze_turn",), ("load_draft",)}
            and state.get("current")
            and state["current"].get("id") != key
        ):
            await graph.ainvoke(None, self.config(sid), durability="sync")
            state = dict((await graph.aget_state(self.config(sid))).values)
            snapshot = await graph.aget_state(self.config(sid))
        # Recover an invocation interrupted by process death. Sync durability commits
        # every node before advancing; rerun only pending nodes, never a completed LLM.
        if state.get("request_id") == key or state.get("current", {}).get("id") == key:
            if self.digest(state["current"]) != self.digest({**payload, "id": key}):
                raise AppError(
                    "idempotency_conflict", "This request key was used with different data.", 409
                )
            if snapshot.next and snapshot.next != ("confirm",):
                await graph.ainvoke(None, self.config(sid), durability="sync")
        else:
            if state["stage"] == "saved" or state.get("stopped"):
                raise AppError("session_closed", "This session is no longer open.", 409)
            if len(state["transcripts"]) >= 50:
                raise AppError("too_many_turns", "Please start a new session.", 422)
            current = {**payload, "id": key}
            if snapshot.next == ("confirm",):
                await graph.ainvoke(
                    Command(resume={"action": "change", "current": current}),
                    self.config(sid),
                    durability="sync",
                )
            else:
                await graph.ainvoke(
                    {**state, "current": current}, self.config(sid), durability="sync"
                )
        state = dict((await graph.aget_state(self.config(sid))).values)
        await self.remember(sid, key, payload, state)
        return state

    async def confirm(self, session: IntakeSession, user: User, consent: bool) -> dict[str, Any]:
        graph = await self.ready()
        sid = str(session.id)
        state = await self.initial(session)
        if state.get("stopped") or state.get("conflicts") or not state["draft"]:
            raise AppError("confirmation_required", "Please complete and review the details.", 409)
        snapshot = await graph.aget_state(self.config(sid))
        if state["stage"] == "saved":
            # A crash after persist may still need the durable enqueue node.
            if snapshot.next:
                await graph.ainvoke(None, self.config(sid), durability="sync")
        elif snapshot.next == ("confirm",) and consent:
            await graph.ainvoke(
                Command(
                    resume={
                        "action": "save",
                        "owner_id": str(user.id),
                        "owner_role": user.role,
                        "consent": consent,
                    }
                ),
                self.config(sid),
                durability="sync",
            )
        elif state["stage"] == "confirmed" and state.get("owner_id") == str(user.id):
            await graph.ainvoke(None, self.config(sid), durability="sync")
        else:
            raise AppError(
                "confirmation_required", "Please confirm the read-back before saving.", 409
            )
        return dict((await graph.aget_state(self.config(sid))).values)

    async def clip(self, sid: str, turn_id: str, index: int, transcript: str, final: bool) -> str:
        async with self.factory() as db, db.begin():
            old = await db.get(IntakeClip, (UUID(sid), turn_id, index))
            if old and old.transcript != transcript:
                raise AppError(
                    "clip_conflict", "This clip index already contains different speech.", 409
                )
            await db.execute(
                insert(IntakeClip)
                .values(
                    session_id=UUID(sid), turn_id=turn_id, clip_index=index, transcript=transcript
                )
                .on_conflict_do_nothing()
            )
            clips = list(
                (
                    await db.scalars(
                        select(IntakeClip)
                        .where(IntakeClip.session_id == UUID(sid), IntakeClip.turn_id == turn_id)
                        .order_by(IntakeClip.clip_index)
                    )
                ).all()
            )
            if final and [c.clip_index for c in clips] != list(range(index + 1)):
                raise AppError("clip_gap", "Please send the missing clips in order.", 409)
            return " ".join(c.transcript for c in clips)

    async def attach_photo(self, session: IntakeSession, photo: Photo) -> None:
        state = await self.initial(session)
        if state["stage"] in {"confirmed", "saved"} or state.get("stopped"):
            raise AppError("session_closed", "This session is no longer open.", 409)
        async with self.factory() as db, db.begin():
            db.add(photo)
            await db.flush()
        graph = await self.ready()
        ids = [*state["photo_ids"], str(photo.id)]
        # Initialize a checkpoint without running the graph on photo-only uploads.
        await graph.aupdate_state(
            self.config(str(session.id)), {**state, "photo_ids": ids}, as_node="record_turn"
        )

    async def enqueue(self, person_id: str) -> bool:
        try:
            queue = ArqRedis(connection_pool=self.redis.connection_pool)
            await queue.enqueue_job(
                "match_new_record",
                person_id,
                _job_id=f"intake:{person_id}",
                _queue_name="khoj:matching",
            )
        except RedisError:
            return False
        async with self.factory() as db, db.begin():
            job = await db.get(IntakeMatchJob, UUID(person_id))
            if job:
                job.enqueued_at = datetime.now(UTC)
        return True
