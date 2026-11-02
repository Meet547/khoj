import asyncio
import io
import subprocess
from typing import Literal, cast

import httpx
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.audio import AudioError, to_wav16k
from app.config import Settings
from app.core.errors import AppError
from app.deps import get_config
from app.integrations.gnani import DEFAULT_TOPIC, Gnani, GnaniError, tts_prepare
from app.integrations.storage import Storage, tts_key

Language = Literal["auto", "hi", "en", "mr", "bn", "ta", "te", "kn", "ml", "gu", "pa"]
MAX_BYTES = 2 * 1024 * 1024
router = APIRouter(prefix="/api/voice")


def get_gnani(request: Request) -> Gnani:
    return cast(Gnani, request.app.state.gnani)


def get_storage(request: Request) -> Storage:
    return cast(Storage, request.app.state.storage)


def provider_error(exc: GnaniError) -> AppError:
    if exc.status == 429:
        return AppError("busy", "busy", 429, retryable=True, retry_after=1)
    if exc.status >= 500:
        return AppError(
            "voice_unavailable", "Speech service is unavailable. Please retry.", 503, retryable=True
        )
    if exc.status in {401, 403}:
        return AppError(
            "voice_unavailable", "Speech service is not configured or has no credits.", 503
        )
    return AppError(
        "invalid_audio", "Speech could not be processed. Please use a clip up to 30 seconds.", 422
    )


@router.post("/stt")
async def stt(
    audio: UploadFile = File(...),
    lang: Language = Form("hi"),
    topic: str = Form(DEFAULT_TOPIC, max_length=1600),
    gnani: Gnani = Depends(get_gnani),
) -> dict[str, object]:
    try:
        data = await audio.read(MAX_BYTES + 1)
    finally:
        await audio.close()
    if len(data) > MAX_BYTES:
        raise AppError("audio_too_large", "Audio must be at most 2 MB.", 413)
    try:
        wav = await asyncio.to_thread(to_wav16k, data)
    except (AudioError, subprocess.TimeoutExpired, OSError) as exc:
        message = (
            "Audio is longer than 30 seconds. Record a shorter clip."
            if isinstance(exc, AudioError) and "30 seconds" in str(exc)
            else "Could not decode audio. Please record a new clip up to 30 seconds."
        )
        raise AppError("invalid_audio", message, 422, retryable=False) from exc
    try:
        result = await gnani.transcribe(
            wav, ui_lang="hi" if lang == "auto" else lang, topic=topic, auto=lang == "auto"
        )
    except GnaniError as exc:
        raise provider_error(exc) from exc
    except (httpx.HTTPError, TimeoutError) as exc:
        raise AppError(
            "voice_unavailable", "Speech service is unavailable. Please retry.", 503, retryable=True
        ) from exc
    return {
        "transcript": result.transcript,
        "detectedLang": result.detected_language,
        "empty": result.empty,
    }


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    lang: Language = "hi"


def mp3(data: bytes, *, url: str | None = None, hit: bool = False) -> StreamingResponse:
    headers = {"X-TTS-Cache": "hit" if hit else "miss"}
    if url:
        headers.update({"X-Audio-URL": url, "Location": url})
    return StreamingResponse(io.BytesIO(data), media_type="audio/mpeg", headers=headers)


@router.post("/tts")
async def tts(
    body: TTSRequest,
    request: Request,
    gnani: Gnani = Depends(get_gnani),
    storage: Storage = Depends(get_storage),
    config: Settings = Depends(get_config),
) -> StreamingResponse:
    if not body.text.strip():
        raise AppError("invalid_request", "Text must not be empty.", 422)
    key = tts_key(body.text, body.lang, config.tts_voice, config.tts_model, config.tts_speed)
    try:
        data = await storage.get(key)
        hit = data is not None
        if data is None:
            resources = request.app.state.intake_resources
            if body.lang in resources.templates and body.text in resources.static_sentences(
                body.lang
            ):
                raise AppError(
                    "speech_not_prepared", "This prompt audio has not been prepared.", 503
                )
            data = await gnani.speak(
                tts_prepare(body.text, body.lang),
                ui_lang=body.lang,
                voice=config.tts_voice,
                model=config.tts_model,
                speed=config.tts_speed,
            )
            await storage.put(key, data)
        return mp3(data, url=storage.signed_url(key, str(request.base_url)), hit=hit)
    except GnaniError as exc:
        raise provider_error(exc) from exc
    except (httpx.HTTPError, TimeoutError, OSError) as exc:
        raise AppError(
            "voice_unavailable",
            "Speech service or cache is unavailable. Please retry.",
            503,
            retryable=True,
        ) from exc


@router.get("/cache/{key}")
async def cached_audio(
    key: str, expires: int, signature: str, storage: Storage = Depends(get_storage)
) -> StreamingResponse:
    storage.verify(key, expires, signature)
    data = await storage.get(key)
    if data is None:
        raise AppError("not_found", "Audio not found.", 404)
    return mp3(data, hit=True)
