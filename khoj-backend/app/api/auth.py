import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.errors import AppError
from app.core.rate_limit import CHALLENGE, RateLimiter, eval_script
from app.core.security import PhoneVault, decode_access, issue_access, token_digest
from app.db.models import AuthSession, RefreshToken, User
from app.deps import get_config, get_db, get_redis, require_user
from app.integrations.sms import OtpProvider

router = APIRouter(prefix="/api/auth", tags=["auth"])
DEMO_ROLES = {
    "9000000001": "citizen",
    "9000000002": "volunteer",
    "9000000003": "officer",
    "9000000004": "admin",
}


class PhoneInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    phone: str = Field(pattern=r"^[6-9]\d{9}$", max_length=10)


class VerifyInput(PhoneInput):
    code: str = Field(pattern=r"^\d{6}$", max_length=6)


class UserView(BaseModel):
    id: UUID
    role: str
    lang: str


class UserResponse(BaseModel):
    user: UserView


class SendResponse(BaseModel):
    ok: bool = True
    demo: bool


def provider(request: Request) -> OtpProvider:
    return cast(OtpProvider, request.app.state.otp_provider)


def user_response(user: User) -> UserResponse:
    return UserResponse(user=UserView(id=user.id, role=user.role, lang=user.lang))


def set_cookies(
    response: Response, settings: Settings, user: User, session: AuthSession, refresh: str
) -> None:
    response.set_cookie(
        "khoj_session",
        issue_access(settings, user.id, user.role, session.id),
        max_age=settings.access_ttl_seconds,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        "khoj_refresh",
        refresh,
        max_age=max(0, int((session.expires_at - datetime.now(UTC)).total_seconds())),
        httponly=True,
        secure=True,
        samesite="lax",
        path="/api/auth",
    )
    response.headers["Cache-Control"] = "no-store"


async def limit(
    request: Request, phone: str, purpose: str, maximum: int, redis: Redis, settings: Settings
) -> str:
    digest = PhoneVault(settings).digest(phone).hex()
    # Trust the immediate peer, not spoofable X-Forwarded-For headers. Configure proxy trust at deployment.
    address = request.client.host if request.client else "unknown"
    ip = hashlib.sha256(address.encode()).hexdigest()
    limiter = RateLimiter(redis)
    await limiter.check(f"{purpose}:ip:{ip}", maximum * 10)
    await limiter.check(f"{purpose}:phone:{digest}", maximum)
    return digest


@router.post("/otp/send", response_model=SendResponse)
async def send_otp(
    body: PhoneInput,
    request: Request,
    settings: Settings = Depends(get_config),
    redis: Redis = Depends(get_redis),
    otp: OtpProvider = Depends(provider),
) -> SendResponse:
    digest = await limit(request, body.phone, "send", 5, redis, settings)
    await otp.send(body.phone)
    await redis.set("otp:" + digest, "pending", ex=300)
    return SendResponse(demo=otp.demo)


@router.post("/otp/verify", response_model=UserResponse)
async def verify_otp(
    body: VerifyInput,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_config),
    redis: Redis = Depends(get_redis),
    otp: OtpProvider = Depends(provider),
) -> UserResponse:
    digest = await limit(request, body.phone, "verify", 10, redis, settings)
    if not await redis.exists("otp:" + digest) or not await otp.verify(body.phone, body.code):
        raise AppError("invalid_code", "That code didn't match. Try again.", 400)
    # Consume the challenge atomically: two requests cannot redeem the same OTP.
    if not await eval_script(redis, CHALLENGE, 1, "otp:" + digest):
        raise AppError("invalid_code", "Please request a new code.", 400)
    vault = PhoneVault(settings)
    role = DEMO_ROLES.get(body.phone, "citizen") if otp.demo else "citizen"
    result = await db.execute(
        insert(User)
        .values(
            phone_hash=vault.digest(body.phone),
            phone_enc=vault.encrypt(body.phone),
            role=role,
            lang="hi",
        )
        .on_conflict_do_nothing(index_elements=[User.phone_hash])
        .returning(User.id)
    )
    user_id = result.scalar_one_or_none()
    user = (
        await db.scalar(select(User).where(User.phone_hash == vault.digest(body.phone)))
        if user_id is None
        else await db.get(User, user_id)
    )
    if user is None:
        raise AppError("temporarily_unavailable", "Please try again.", 503, retryable=True)
    session = AuthSession(
        user_id=user.id,
        expires_at=datetime.now(UTC) + timedelta(seconds=settings.refresh_ttl_seconds),
    )
    db.add(session)
    await db.flush()
    refresh = secrets.token_urlsafe(48)
    db.add(
        RefreshToken(
            session_id=session.id, token_hash=token_digest(refresh), expires_at=session.expires_at
        )
    )
    await db.flush()
    set_cookies(response, settings, user, session, refresh)
    return user_response(user)


@router.post("/refresh", response_model=UserResponse)
async def refresh_session(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_config),
) -> UserResponse:
    raw = request.cookies.get("khoj_refresh", "")
    now = datetime.now(UTC)
    # Lock the family and token together; concurrent refresh/replay requests serialize.
    row = (
        await db.execute(
            select(RefreshToken, AuthSession)
            .join(AuthSession, RefreshToken.session_id == AuthSession.id)
            .where(RefreshToken.token_hash == token_digest(raw))
            .with_for_update()
        )
    ).one_or_none()
    if row is None:
        raise AppError("unauthorized", "Please sign in again.", 401)
    token, session = row
    if token.consumed_at is not None:
        session.revoked_at = now
        # Persist replay revocation even though the request returns an error.
        await db.commit()
        raise AppError("unauthorized", "Please sign in again.", 401)
    if session.revoked_at is not None or session.expires_at <= now or token.expires_at <= now:
        raise AppError("unauthorized", "Please sign in again.", 401)
    user = await db.get(User, session.user_id)
    if user is None:
        raise AppError("unauthorized", "Please sign in again.", 401)
    token.consumed_at = now
    refresh = secrets.token_urlsafe(48)
    db.add(
        RefreshToken(
            session_id=session.id, token_hash=token_digest(refresh), expires_at=session.expires_at
        )
    )
    await db.flush()
    set_cookies(response, settings, user, session, refresh)
    return user_response(user)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_config),
) -> None:
    ids: set[UUID] = set()
    access = request.cookies.get("khoj_session")
    if access:
        try:
            ids.add(decode_access(settings, access)[2])
        except AppError:
            pass
    refresh = request.cookies.get("khoj_refresh")
    if refresh:
        token = await db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_digest(refresh))
        )
        if token:
            ids.add(token.session_id)
    for session_id in ids:
        session = await db.get(AuthSession, session_id, with_for_update=True)
        if session:
            session.revoked_at = datetime.now(UTC)
    response.delete_cookie("khoj_session", path="/", httponly=True, secure=True, samesite="lax")
    response.delete_cookie(
        "khoj_refresh", path="/api/auth", httponly=True, secure=True, samesite="lax"
    )


@router.get("/me", response_model=UserResponse)
async def me(response: Response, user: User = Depends(require_user)) -> UserResponse:
    response.headers["Cache-Control"] = "no-store"
    return user_response(user)
