"""Ollama Cloud client. POST https://ollama.com/api/chat with 'Authorization: Bearer <key>'.
Structured output goes in `format` (a JSON schema). `think` is bool, or low/medium/high for gpt-oss."""

from typing import Any, cast

import httpx


class OllamaError(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(f"Ollama {status}: {body[:200]}")
        self.status = status


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 90,
    ):
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._c = httpx.AsyncClient(
            base_url=base_url, headers=headers, timeout=timeout, transport=transport
        )

    async def chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        *,
        schema: dict[str, Any] | None = None,
        think: bool | str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if schema:
            body["format"] = schema
        if think is not None:
            body["think"] = think
        if max_tokens:
            body["options"]["num_predict"] = max_tokens
        r = await self._c.post("/api/chat", json=body)
        if r.status_code >= 400:
            raise OllamaError(r.status_code, r.text)
        return cast(dict[str, Any], r.json())

    async def tags(self) -> list[str]:
        r = await self._c.get("/api/tags")
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]

    async def aclose(self) -> None:
        await self._c.aclose()
