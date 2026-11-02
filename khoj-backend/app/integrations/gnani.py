"""Gnani Vachana speech client (verified against docs.gnani.ai).
STT: POST /stt/v3 multipart (audio_file, language_code, model=prisma-v3.0). Max 30 s. WAV/MP3/OGG/FLAC/AAC/M4A only.
     No per-word confidence is returned, so the read-back step stays mandatory.
TTS: POST /api/v1/tts/inference JSON -> binary audio. Header: X-API-Key-ID."""

import asyncio
import json
import re
import unicodedata
from collections.abc import Awaitable, Callable
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.errors import AppError
from app.core.semaphore import RedisSemaphore

LANG = {
    "en": "en-IN",
    "hi": "hi-IN",
    "mr": "mr-IN",
    "bn": "bn-IN",
    "ta": "ta-IN",
    "pa": "pa-IN",
    "gu": "gu-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "te": "te-IN",
}
DEFAULT_TOPIC = (
    "A person in India describing someone who is missing: name, age, clothes, scars or marks, "
    "language spoken, and the place and time last seen."
)
SLOT_WAIT_SECONDS = 8


class GnaniError(Exception):
    def __init__(self, status: int, kind: str, msg: str):
        super().__init__(f"Gnani {status} {kind}: {msg}")
        self.status, self.kind = status, kind


@dataclass
class STT:
    transcript: str
    detected_language: str | None
    request_id: str | None
    truncated: bool = False

    @property
    def empty(self) -> bool:
        return not self.transcript.strip()


def _err(r: httpx.Response) -> GnaniError:
    try:
        b = r.json()
    except Exception:
        return GnaniError(r.status_code, "HTTP", r.text[:200])
    if isinstance(b.get("detail"), dict):  # auth / rate-limit shape
        d = b["detail"]
        return GnaniError(r.status_code, d.get("error_code", "HTTP"), d.get("message", ""))
    if isinstance(b.get("error"), dict):  # standard envelope
        return GnaniError(
            r.status_code, b["error"].get("type", "HTTP"), b["error"].get("message", "")
        )
    return GnaniError(r.status_code, b.get("code", "HTTP"), str(b)[:200])


class Gnani:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.vachana.ai",
        transport: httpx.AsyncBaseTransport | None = None,
        stt_slots: int = 1,
        tts_slots: int = 2,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        shared_stt: RedisSemaphore | None = None,
    ):
        self._c = httpx.AsyncClient(
            base_url=base_url, headers={"X-API-Key-ID": api_key}, timeout=60, transport=transport
        )
        self._stt, self._tts, self._sleep = (
            asyncio.Semaphore(stt_slots),
            asyncio.Semaphore(tts_slots),
            sleep,
        )
        self.shared_stt = shared_stt

    async def _post(self, sem: asyncio.Semaphore, path: str, **kw: Any) -> httpx.Response:
        async with AsyncExitStack() as stack:
            try:
                async with asyncio.timeout(SLOT_WAIT_SECONDS):
                    # Keep the in-process semaphore as the first layer.
                    await stack.enter_async_context(sem)
                    if sem is self._stt and self.shared_stt is not None:
                        await stack.enter_async_context(self.shared_stt.lease())
            except TimeoutError as exc:
                raise AppError("busy", "busy", 429, retryable=True, retry_after=1) from exc
            async with asyncio.timeout(270):
                return await self._post_retries(path, **kw)

    async def _post_retries(self, path: str, **kw: Any) -> httpx.Response:
        for i in range(4):
            r = await self._c.post(path, **kw)
            if r.status_code in (429, 503, 504) and i < 3:
                await self._sleep(0.5 * 2**i)
                continue
            return r
        raise AssertionError("unreachable")

    async def transcribe(
        self,
        audio: bytes,
        *,
        ui_lang: str = "hi",
        filename: str = "speech.wav",
        topic: str | None = DEFAULT_TOPIC,
        keyterms: list[str] | None = None,
        auto: bool = False,
    ) -> STT:
        code = LANG[ui_lang]
        lang_param = (
            "indic-auto" if auto else (f"{code},en-IN" if code != "en-IN" else "en-IN,hi-IN")
        )
        data = {"model": "prisma-v3.0", "language_code": lang_param}
        if topic:
            data["topic"] = topic[:1600]
        if keyterms:
            data["keyterms"] = json.dumps(keyterms[:200], ensure_ascii=False)
        r = await self._post(
            self._stt, "/stt/v3", files={"audio_file": (filename, audio)}, data=data
        )
        if r.status_code != 200:
            raise _err(r)
        b = r.json()
        return STT(
            b.get("transcript", ""),
            b.get("detected_language_code"),
            b.get("request_id"),
            bool(b.get("truncated")),
        )

    async def speak(
        self,
        text: str,
        *,
        ui_lang: str = "hi",
        voice: str = "Shivani",
        speed: float = 1.0,
        model: str = "timbre-v3.0",
    ) -> bytes:
        body = {
            "text": text,
            "voice": voice,
            "model": model,
            "language": LANG.get(ui_lang, "auto"),
            "speed": speed,
            "audio_config": {"container": "mp3", "sample_rate": 24000, "bitrate": "64k"},
        }
        r = await self._post(self._tts, "/api/v1/tts/inference", json=body)
        if r.status_code != 200 or "json" in r.headers.get("content-type", ""):
            raise _err(r)
        return r.content

    async def aclose(self) -> None:
        await self._c.aclose()


def spell_id(case_no: str) -> str:
    """Case numbers must be read out character by character, not as one big number."""
    return " ".join(ch for ch in case_no if ch.isalnum())


def tts_prepare(text: str, lang: str) -> str:
    """Keep identifiers unambiguous even when provider TN would read a cardinal."""
    # Read 2026-11-02. TODO: extend dates/currency/abbreviations using Gnani's TN
    # guide, without applying cardinal-number rules to case IDs:
    # https://docs.gnani.ai/api/TTS/tts-input-formating
    # The guide warns about repeated-digit compression and slash-ID ambiguity.
    digits = {
        "hi": "शून्य एक दो तीन चार पाँच छह सात आठ नौ".split(),
        "mr": "शून्य एक दोन तीन चार पाच सहा सात आठ नऊ".split(),
        "en": "zero one two three four five six seven eight nine".split(),
    }.get(lang, "zero one two three four five six seven eight nine".split())

    def spell(match: re.Match[str]) -> str:
        chars = spell_id(match.group()).split()
        return " ".join(digits[unicodedata.decimal(ch)] if ch.isdecimal() else ch for ch in chars)

    # Match full mixed case numbers before bare digit strings (Unicode digits too).
    return re.sub(r"\b(?=[A-Za-z\d/-]*\d)[A-Za-z\d]+(?:[-/][A-Za-z\d]+)*\b|\d+", spell, text)
