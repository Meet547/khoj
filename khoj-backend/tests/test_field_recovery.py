import json

import httpx
import pytest

from app.graph.resources import Resources
from app.integrations.ollama import OllamaClient
from app.llm import LLM
from scripts.field_recovery import extract_detail, fields, write_detail


@pytest.mark.asyncio
async def test_detail_preserves_failed_attempts_and_final_model(tmp_path):
    models = []

    def fake_gateway(request):
        model = json.loads(request.content)["model"]
        models.append(model)
        if model == "primary":
            return httpx.Response(503 if len(models) == 1 else 400)
        return httpx.Response(200, json={"message": {"content": '{"intent":"other"}'}})

    async def no_sleep(_delay):
        pass

    client = OllamaClient("https://ollama.test", "", transport=httpx.MockTransport(fake_gateway))
    llm = LLM(
        client, {"roles": {"turn": {"primary": "primary", "fallback": ["backup"]}}}, sleep=no_sleep
    )
    try:
        item = {"expected": dict.fromkeys(fields)}
        detail = await extract_detail(llm, Resources(), item, "Synthetic input.", "en")
    finally:
        await client.aclose()

    path = tmp_path / "detail.jsonl"
    with path.open("x") as handle:
        write_detail(handle, detail)
    saved = json.loads(path.read_text())
    assert saved["model"] == "backup"
    assert saved["trail"] == ["primary: HTTP 503", "primary: HTTP 400"]
    attempts = saved["attempts"]
    assert [attempt["model"] for attempt in attempts] == models == ["primary", "primary", "backup"]
    assert [attempt["retry"] for attempt in attempts] == [1, 2, 1]
    assert [attempt["fallback"] for attempt in attempts] == [False, False, True]
    assert [attempt["outcome"] for attempt in attempts] == ["http_error", "http_error", "success"]
    assert all(attempt["phase"] == "initial" for attempt in attempts)
    assert all(attempt["timeout_seconds"] == 6 and attempt["wall_ms"] >= 0 for attempt in attempts)
