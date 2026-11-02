from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_redis

router = APIRouter()


@router.get("/api/health")
async def health(
    db: AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis)
) -> JSONResponse:
    checks = {"database": False, "redis": False}
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except (SQLAlchemyError, OSError):
        await db.rollback()
    try:
        checks["redis"] = bool(await redis.ping())
    except RedisError:
        pass
    ok = all(checks.values())
    return JSONResponse({"ok": ok, "checks": checks}, status_code=200 if ok else 503)
