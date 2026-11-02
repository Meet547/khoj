"""Static speech is cache-only. Dynamic sentences have durable, independently playable URLs."""

import asyncio
import hashlib
import hmac
import logging
import re
import time
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.core.errors import AppError
from app.db.models import SpeechSegment
from app.graph.resources import Resources
from app.integrations.gnani import Gnani, tts_prepare
from app.integrations.storage import Storage, tts_key

logger = logging.getLogger("khoj")


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?।])\s+", text) if s.strip()]


class IntakeAudio:
    def __init__(
        self,
        config: Settings,
        storage: Storage,
        gnani: Gnani,
        resources: Resources,
        factory: async_sessionmaker[AsyncSession],
    ):
        self.config, self.storage, self.gnani, self.resources, self.factory = (
            config,
            storage,
            gnani,
            resources,
            factory,
        )
        self.tasks: set[asyncio.Task[Any]] = set()
        self.inflight: dict[str, asyncio.Task[bytes | None]] = {}
        self.slots = asyncio.Semaphore(config.gnani_tts_slots)

    def key(self, text: str, lang: str) -> str:
        return tts_key(
            text, lang, self.config.tts_voice, self.config.tts_model, self.config.tts_speed
        )

    def signature(self, key: str, expires: int) -> str:
        return hmac.new(
            self.config.jwt_secret.get_secret_value().encode(),
            f"segment:{key}:{expires}".encode(),
            hashlib.sha256,
        ).hexdigest()

    def url(self, key: str, base: str) -> str:
        expires = int(time.time()) + self.config.tts_url_ttl
        return f"{base.rstrip('/')}/api/voice/segments/{key}?expires={expires}&signature={self.signature(key, expires)}"

    def verify(self, key: str, expires: int, signature: str) -> None:
        if (
            not re.fullmatch(r"[a-f0-9]{64}", key)
            or expires <= time.time()
            or not hmac.compare_digest(signature, self.signature(key, expires))
        ):
            raise AppError("forbidden", "Audio link has expired or is invalid.", 403)

    async def ensure(self, key: str) -> bytes | None:
        try:
            cached = await self.storage.get(key)
            if cached is not None:
                return cached
            async with self.factory() as db:
                segment = await db.get(SpeechSegment, key)
                if segment is None:
                    return None
            # Admission happens here so a long readback does not exhaust the
            # low-level client's bounded local queue while waiting its turn.
            async with self.slots:
                data = await self.gnani.speak(
                    tts_prepare(segment.text, segment.lang),
                    ui_lang=segment.lang,
                    voice=segment.voice,
                    model=segment.model,
                    speed=segment.speed,
                )
            await self.storage.put(key, data)
            return data
        except Exception:
            logger.warning("intake_tts_failed")
            return None

    def start(self, key: str) -> asyncio.Task[bytes | None]:
        old = self.inflight.get(key)
        if old and not old.done():
            return old
        task = asyncio.create_task(self.ensure(key))
        self.inflight[key] = task
        self.tasks.add(task)

        def done(completed: asyncio.Task[Any]) -> None:
            self.tasks.discard(completed)
            self.inflight.pop(key, None)

        task.add_done_callback(done)
        return task

    async def prepare(self, text: str, lang: str, base: str) -> list[str | None]:
        statics = self.resources.static_sentences(lang)
        # Preserve whole static template keys; don't accidentally synthesize fragments.
        if text in statics:
            key = self.key(text, lang)
            return (
                [self.storage.signed_url(key, base)]
                if await self.storage.get(key) is not None
                else []
            )
        parts = sentences(text)
        urls: list[str | None] = []
        tasks: list[tuple[int, asyncio.Task[bytes | None]]] = []
        # Known static pieces, including the readback intro/confirmation, are never
        # synthesized on a request. Pregen writes whole template audio files.
        for part in parts:
            key = self.key(part, lang)
            if part in statics or any(part in sentences(s) for s in statics):
                cached = await self.storage.get(key)
                urls.append(self.storage.signed_url(key, base) if cached is not None else None)
                continue
            async with self.factory() as db, db.begin():
                await db.execute(
                    insert(SpeechSegment)
                    .values(
                        key=key,
                        text=part,
                        lang=lang,
                        voice=self.config.tts_voice,
                        model=self.config.tts_model,
                        speed=self.config.tts_speed,
                    )
                    .on_conflict_do_nothing()
                )
            urls.append(self.url(key, base))
            tasks.append((len(urls) - 1, self.start(key)))
        # A cached opening sentence can play immediately. Otherwise await only
        # the first dynamic sentence; later segments continue in the background.
        if tasks and (tasks[0][0] == 0 or not urls[0]):
            index, task = tasks[0]
            if await asyncio.shield(task) is None:
                urls[index] = None
        return urls

    async def close(self) -> None:
        for task in list(self.tasks):
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
