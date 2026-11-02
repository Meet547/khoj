import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from app.integrations.ollama import OllamaClient

logger = logging.getLogger("khoj")


class Capabilities:
    def __init__(self, client: OllamaClient, cfg: dict[str, Any]):
        self.client, self.cfg = client, cfg
        self.available: set[str] | None = None
        self.report: dict[str, Any] = {}

    async def probe(self) -> dict[str, Any]:
        error = None
        try:
            async with asyncio.timeout(10):
                self.available = set(await self.client.tags())
        except Exception:
            # Keep startup alive; never expose provider exceptions or credentials.
            self.available = None
            error = "ollama_unavailable"
            logger.warning("ollama_probe_failed")
        referenced = set()
        roles = {}
        for role, cfg in self.cfg["roles"].items():
            models = {cfg["primary"], *cfg.get("fallback", [])}
            overrides = {
                lang: values[role]
                for lang, values in self.cfg.get("language_overrides", {}).items()
                if role in values
            }
            models.update(overrides.values())
            referenced.update(models)
            missing = sorted(models - (self.available or set()))
            roles[role] = {
                "primary": cfg["primary"],
                "missing": missing,
                "degraded": self.available is None or bool(missing),
                "primaryMissing": cfg["primary"] not in (self.available or set()),
                "languageOverrides": overrides,
            }
        self.report = {
            "checkedAt": datetime.now(UTC).isoformat(),
            "error": error,
            "missing": sorted(referenced - (self.available or set())),
            "roles": roles,
            "degraded": any(r["degraded"] for r in roles.values()),
        }
        if self.report["degraded"]:
            logger.warning("ollama_roles_degraded")
        else:
            logger.info("ollama_probe_ok")
        return self.report
