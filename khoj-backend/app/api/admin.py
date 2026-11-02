from typing import Any, cast

from fastapi import APIRouter, Depends, Request

from app.capabilities import Capabilities
from app.deps import require_role
from app.usage import Usage

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_role("admin"))])


@router.get("/health")
async def health(request: Request) -> dict[str, Any]:
    report = await cast(Capabilities, request.app.state.capabilities).probe()
    return {"ok": not report["degraded"], "ollama": report}


@router.get("/usage")
async def usage(request: Request) -> dict[str, Any]:
    return await cast(Usage, request.app.state.usage).snapshot()
