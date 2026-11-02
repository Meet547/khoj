from collections.abc import AsyncIterator, Callable, Coroutine
from datetime import UTC, datetime
from typing import Any, Literal, cast

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.core.errors import AppError
from app.core.security import decode_access
from app.db.models import AuthSession, User

Role = Literal["citizen", "volunteer", "officer", "admin"]


def get_config(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_redis(request: Request) -> Redis:
    return cast(Redis, request.app.state.redis)


def get_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return cast(async_sessionmaker[AsyncSession], request.app.state.db_factory)


async def get_db(
    factory: async_sessionmaker[AsyncSession] = Depends(get_factory),
) -> AsyncIterator[AsyncSession]:
    async with factory() as db:
        async with db.begin():
            yield db


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_config)
) -> User | None:
    token = request.cookies.get("khoj_session")
    if not token:
        return None
    user_id, _role, session_id = decode_access(settings, token)
    auth = await db.get(AuthSession, session_id)
    if (
        auth is None
        or auth.user_id != user_id
        or auth.revoked_at is not None
        or auth.expires_at <= datetime.now(UTC)
    ):
        raise AppError("unauthorized", "Please sign in again.", 401)
    user = await db.get(User, user_id)
    if user is None:
        raise AppError("unauthorized", "Please sign in again.", 401)
    return user


async def require_user(user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise AppError("unauthorized", "Please sign in to continue.", 401)
    return user


def require_role(role: Role) -> Callable[..., Coroutine[Any, Any, User]]:
    async def guard(user: User = Depends(require_user)) -> User:
        # No implicit privilege hierarchy: callers choose the role they require.
        if user.role != role and user.role != "admin":
            raise AppError("forbidden", "You do not have access to this page.", 403)
        return user

    return guard
