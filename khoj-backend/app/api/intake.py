import asyncio
import hashlib
import logging
import secrets
import time
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, Header, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import update

from app.api.voice import Language, mp3, stt
from app.core.errors import AppError
from app.db.models import Photo, Turn, User
from app.deps import get_current_user, require_user
from app.graph.audio import IntakeAudio
from app.graph.service import IntakeService
from app.llm import LLMUnavailable
from app.photos import VisionDescription, sanitize_photo
from app.schemas import FieldName

logger = logging.getLogger("khoj")
router = APIRouter(prefix="/api")
COOKIE = "khoj_intake"


def service(request: Request) -> IntakeService:
    return cast(IntakeService, request.app.state.intake)


class SessionRequest(BaseModel):
    kind: Literal["missing", "found"] = "missing"
    lang: Language = "hi"


@router.post("/session")
async def start_session(
    body: SessionRequest,
    request: Request,
    user: User | None = Depends(get_current_user),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key", max_length=128),
) -> Any:
    from fastapi.responses import JSONResponse

    token = request.cookies.get(COOKIE) or secrets.token_urlsafe(32)
    sid = await service(request).create(body.kind, body.lang, token, user, idempotency_key)
    response = JSONResponse({"sessionId": sid})
    response.set_cookie(
        COOKIE, token, httponly=True, secure=True, samesite="lax", max_age=2_592_000, path="/api"
    )
    return response


async def response_for(request: Request, state: dict[str, Any]) -> dict[str, Any]:
    urls: list[str | None] = []
    start = time.monotonic()
    try:
        urls = await cast(IntakeAudio, request.app.state.intake_audio).prepare(
            state.get("reply", ""), state["lang"], str(request.base_url)
        )
    except Exception:
        logger.warning("intake_tts_failed")
    tts_ms = round((time.monotonic() - start) * 1000)
    # Transcript/trace writes are separate from speech delivery: an audio failure never
    # prevents the successful text turn from being returned.
    async with service(request).factory() as db, db.begin():
        await db.execute(
            update(Turn)
            .where(
                Turn.session_id == UUID(state["session_id"]), Turn.idx == len(state["transcripts"])
            )
            .values(tts_ms=tts_ms)
        )
    return {
        "transcript": state["transcripts"][-1] if state["transcripts"] else "",
        "replyText": state.get("reply", ""),
        "replyAudioUrl": urls[0] if urls and all(urls) else None,
        "replyAudioUrls": urls,
        "draft": state["draft"],
        "stage": state["stage"],
        "nextField": state.get("next_field"),
        "readbackText": state.get("readback_text"),
        "conflicts": state.get("conflicts", {}),
        "degraded": state.get("degraded", False),
    }


@router.get("/session/{session_id}")
async def resume_session(
    session_id: UUID, request: Request, user: User | None = Depends(get_current_user)
) -> dict[str, Any]:
    intake = service(request)
    async with intake.locked(str(session_id), request.cookies.get(COOKIE), user) as session:
        state = await intake.initial(session)
        return await response_for(request, state)


@router.post("/turn")
async def turn(
    request: Request,
    sessionId: UUID = Form(...),
    text: str | None = Form(None, max_length=12000),
    audio: UploadFile | None = File(None),
    clipIndex: int | None = Form(None, ge=0, le=49),
    finalClip: bool = Form(True),
    turnId: str | None = Form(None, max_length=100),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key", max_length=128),
    user: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    if (text is None) == (audio is None):
        raise AppError("invalid_request", "Send either text or audio.", 422)
    intake = service(request)
    sid = str(sessionId)
    async with intake.locked(sid, request.cookies.get(COOKIE), user) as session:
        start = time.monotonic()
        mode = "voice" if audio is not None else "text"
        if audio is not None:
            from app.integrations.gnani import DEFAULT_TOPIC

            result = await stt(
                audio=audio,
                lang=cast(Any, session.lang),
                topic=DEFAULT_TOPIC,
                gnani=request.app.state.gnani,
            )
            text = str(result["transcript"])
            detected = str(result.get("detectedLang") or "").split("-")[0]
            if detected in intake.resources.templates:
                intake.resources.language(detected, production=intake.settings.env == "production")
                session.lang = detected
        transcript = text or ""
        stt_ms = round((time.monotonic() - start) * 1000) if mode == "voice" else 0
        if clipIndex is not None:
            state = await intake.initial(session)
            group = turnId or f"turn:{len(state['transcripts'])}"
            transcript = await intake.clip(sid, group, clipIndex, transcript, finalClip)
            if len(transcript) > 12000:
                raise AppError("invalid_request", "Please use a shorter description.", 422)
            if not finalClip:
                return {
                    "transcript": transcript,
                    "replyText": "",
                    "replyAudioUrl": None,
                    "replyAudioUrls": [],
                    "draft": state["draft"],
                    "stage": state["stage"],
                    "nextField": state.get("next_field"),
                    "readbackText": state.get("readback_text"),
                }
        payload = {"text": transcript, "mode": mode, "stt_ms": stt_ms, "lang": session.lang}
        # Timing is observational, never part of idempotency identity.
        key = "turn:" + (idempotency_key or uuid4().hex)
        state = await intake.run_turn(session, payload, key)
        return await response_for(request, state)


class EditRequest(BaseModel):
    sessionId: UUID
    field: FieldName
    value: str = Field(min_length=1, max_length=1000)


@router.post("/draft/edit")
async def edit(
    body: EditRequest,
    request: Request,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key", max_length=128),
    user: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    intake = service(request)
    async with intake.locked(str(body.sessionId), request.cookies.get(COOKIE), user) as session:
        state = await intake.initial(session)
        payload = {
            "text": body.value,
            "mode": "text",
            "edit": body.field,
            "readback": state["stage"] == "readback",
        }
        state = await intake.run_turn(session, payload, "edit:" + (idempotency_key or uuid4().hex))
        return await response_for(request, state)


class ConfirmRequest(BaseModel):
    sessionId: UUID
    consent: Literal[True]


@router.post("/confirm")
async def confirm(
    body: ConfirmRequest, request: Request, user: User = Depends(require_user)
) -> dict[str, Any]:
    intake = service(request)
    async with intake.locked(str(body.sessionId), request.cookies.get(COOKIE), user) as session:
        state = await intake.confirm(session, user, body.consent)
        return {
            "caseNo": state["case_no"],
            "stage": state["stage"],
            "matchingQueued": state.get("queued", False),
        }


@router.post("/photos")
async def photos(
    request: Request,
    sessionId: UUID = Form(...),
    photo: UploadFile = File(...),
    user: User | None = Depends(get_current_user),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key", max_length=128),
) -> dict[str, Any]:
    intake = service(request)
    async with intake.locked(str(sessionId), request.cookies.get(COOKIE), user) as session:
        try:
            data = await photo.read(10 * 1024 * 1024 + 1)
        finally:
            await photo.close()
        if len(data) > 10 * 1024 * 1024:
            raise AppError("photo_too_large", "Photo must be at most 10 MB.", 413)
        payload = {"photo_hash": hashlib.sha256(data).hexdigest()}
        request_key = "photo:" + (idempotency_key or uuid4().hex)
        prior = await intake.prior(str(session.id), request_key, payload)
        if prior is not None:
            return prior
        data = await asyncio.to_thread(sanitize_photo, data)
        state = await intake.initial(session)
        if len(state["photo_ids"]) >= 5:
            raise AppError("too_many_photos", "Please use at most five photos.", 422)
        if state["stage"] in {"confirmed", "saved"}:
            raise AppError("session_closed", "This session is no longer open.", 409)
        vision: dict[str, Any] = {}
        try:
            result = await intake.llm.run(
                "vision",
                [
                    {"role": "system", "content": intake.resources.prompts["vision"]},
                    {"role": "user", "content": "Describe only clothing, marks and scene."},
                ],
                images=[data],
                schema_model=VisionDescription,
                lang=session.lang,
            )
            if result.parsed:
                vision = result.parsed.model_dump()
            vision["_trace"] = {
                "model": result.model,
                "prompt_hash": intake.resources.hashes["vision"],
            }
        except LLMUnavailable:
            vision["_degraded"] = True
        photo_id = uuid4()
        key = hashlib.sha256(f"{session.id}:{photo_id}".encode()).hexdigest()
        await request.app.state.storage.put_photo(key, data)
        row = Photo(
            id=photo_id, session_id=session.id, r2_key=f"photos/{key}.jpg", vision_desc=vision
        )
        await intake.attach_photo(session, row)
        response = {"photoIds": [str(photo_id)]}
        await intake.remember(str(session.id), request_key, payload, response)
        return response


@router.get("/voice/segments/{key}")
async def segment(key: str, expires: int, signature: str, request: Request) -> Any:
    audio = cast(IntakeAudio, request.app.state.intake_audio)
    audio.verify(key, expires, signature)
    data = await asyncio.shield(audio.start(key))
    if data is None:
        raise AppError(
            "audio_unavailable",
            "Speech is unavailable. Please use the captions.",
            503,
            retryable=True,
        )
    return mp3(data, hit=True)
