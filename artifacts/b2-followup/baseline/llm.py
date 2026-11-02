"""Role-based model gateway: pick model by role + language, enforce JSON schema, repair once, fall back, back off."""

import asyncio
import base64
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from .capabilities import Capabilities
from .integrations.ollama import OllamaClient, OllamaError
from .privacy import redact
from .usage import BudgetExceeded, Usage

RETRY = {429, 500, 502, 503, 504}


class LLMUnavailable(Exception):
    pass


@dataclass
class LLMResult:
    model: str
    text: str
    parsed: BaseModel | None = None
    latency_ms: int = 0
    trail: list[str] = field(default_factory=list)  # every attempt, for tracing
    degraded: bool = False
    skipped: bool = False


class LLM:
    def __init__(
        self,
        client: OllamaClient,
        cfg: dict[str, Any],
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        usage: Usage | None = None,
        capabilities: Capabilities | None = None,
    ):
        self.client, self.cfg, self._sleep = client, cfg, sleep
        self.usage, self.capabilities = usage, capabilities

    def chain(self, role: str, lang: str | None = None) -> list[str]:
        r = self.cfg["roles"][role]
        first = (self.cfg.get("language_overrides", {}).get(lang or "", {}) or {}).get(role) or r[
            "primary"
        ]
        out: list[str] = []
        for m in [first, r["primary"], *r.get("fallback", [])]:
            if m not in out:
                out.append(m)
        return out

    async def _call(
        self,
        model: str,
        msgs: list[dict[str, Any]],
        schema: dict[str, Any] | None,
        role_cfg: dict[str, Any],
        trail: list[str],
        role: str,
    ) -> dict[str, Any]:
        for i in range(3):  # transport-level retries
            day = await self.usage.reserve(role) if self.usage else ""
            try:
                data = await self.client.chat(
                    model,
                    msgs,
                    schema=schema,
                    think=role_cfg.get("think"),
                    temperature=role_cfg.get("temperature", 0.0),
                )
                if self.usage:
                    await self.usage.tokens(role, day, data)
                return data
            except OllamaError as e:
                trail.append(f"{model}: HTTP {e.status}")
                if e.status not in RETRY or i == 2:
                    raise
                await self._sleep(0.5 * 2**i)
            except (httpx.TransportError, TimeoutError) as e:
                trail.append(f"{model}: transport unavailable")
                if i == 2:
                    raise OllamaError(503, "transport unavailable") from e
                await self._sleep(0.5 * 2**i)

        raise LLMUnavailable("Transport retries exhausted")

    async def run(
        self,
        role: str,
        messages: list[dict[str, Any]],
        *,
        schema_model: type[BaseModel] | None = None,
        lang: str | None = None,
        images: list[bytes] | None = None,
    ) -> LLMResult:
        role_cfg = self.cfg["roles"][role]
        if not role_cfg.get("enabled", True):
            return LLMResult("", "", degraded=True, skipped=True)
        degraded = False
        if self.capabilities:
            degraded = self.capabilities.report.get("roles", {}).get(role, {}).get("degraded", True)
        if self.cfg.get("privacy", {}).get("redact_before_cloud", True):
            messages = [{**m, "content": redact(m["content"])} for m in messages]
        if images:  # attach to the last user message
            messages = [
                *messages[:-1],
                {**messages[-1], "images": [base64.b64encode(b).decode() for b in images]},
            ]
        schema = schema_model.model_json_schema() if schema_model else None
        if schema:
            # Cloud models may accept `format` yet not enforce its schema. State
            # it in the prompt as well, and still validate/repair locally.
            messages = [
                {
                    "role": "system",
                    "content": "Reply with a single JSON object only, without Markdown fences. "
                    "Follow this exact JSON schema (including enum values and array/object types): "
                    + json.dumps(schema, ensure_ascii=False),
                },
                *messages,
            ]
        trail: list[str] = []
        t0 = time.monotonic()
        for model in self.chain(role, lang):
            if (
                self.capabilities
                and self.capabilities.available is not None
                and model not in self.capabilities.available
            ):
                trail.append(f"{model}: unavailable")
                degraded = True
                continue
            msgs = list(messages)
            for repair in (False, True):  # at most one repair attempt per model
                try:
                    data = await self._call(model, msgs, schema, role_cfg, trail, role)
                except BudgetExceeded:
                    return LLMResult(
                        "",
                        "",
                        latency_ms=int((time.monotonic() - t0) * 1000),
                        trail=trail,
                        degraded=True,
                        skipped=True,
                    )
                except OllamaError:
                    break  # go to next model
                text = (data.get("message") or {}).get("content", "")
                budget_hit = False
                if self.usage:
                    budget_hit = (await self.usage.snapshot())["roles"][role]["thresholdHit"]
                result_degraded = degraded or budget_hit or bool(trail)
                if not schema_model:
                    return LLMResult(
                        model,
                        text,
                        None,
                        int((time.monotonic() - t0) * 1000),
                        trail,
                        result_degraded,
                    )
                try:
                    parsed = schema_model.model_validate_json(text)
                    return LLMResult(
                        model,
                        text,
                        parsed,
                        int((time.monotonic() - t0) * 1000),
                        trail,
                        result_degraded,
                    )
                except (ValidationError, json.JSONDecodeError) as e:
                    trail.append(f"{model}: invalid JSON ({type(e).__name__})")
                    if repair:
                        break
                    msgs = [
                        *msgs,
                        {"role": "assistant", "content": text},
                        {
                            "role": "user",
                            "content": "That was not valid JSON for the schema. Reply with only the JSON.",
                        },
                    ]
        raise LLMUnavailable(f"role={role} exhausted: {trail}")
