import asyncio
import copy
import json
from pathlib import Path

import httpx
import pytest

from app.integrations.ollama import OllamaClient
from app.llm import LLM, LLMUnavailable
from app.schemas import Extraction

CFG = {
    "roles": {
        "turn": {
            "primary": "gpt-oss:20b",
            "fallback": ["gemma4:31b"],
            "think": "low",
            "think_by_model": {"gemma4:31b": False},
        }
    },
    "language_overrides": {"hi": {"turn": "gemma4:31b"}},
}
MESSAGES = [{"role": "user", "content": "Leela is 43."}]


def success():
    return httpx.Response(
        200,
        json={
            "message": {"content": '{"fields":[]}', "thinking": "PRIVATE_REASONING"},
            "total_duration": 100_000_000,
            "eval_count": 4,
        },
    )


async def test_attempt_deadline_cancels_and_moves_to_next_model_without_retry():
    cfg = copy.deepcopy(CFG)
    cfg["attempt_timeout_seconds"] = 0.02
    calls = []
    cancelled = []

    async def handler(req):
        body = json.loads(req.content)
        calls.append(body)
        if body["model"] == "gemma4:31b":
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.append(body["model"])
        return success()

    client = OllamaClient("https://ollama.test", "", transport=httpx.MockTransport(handler))
    try:
        result = await LLM(client, cfg).run("turn", MESSAGES, schema_model=Extraction, lang="hi")
        assert [c["model"] for c in calls] == ["gemma4:31b", "gpt-oss:20b"]
        assert cancelled == ["gemma4:31b"] and result.model == "gpt-oss:20b"
        assert [a["outcome"] for a in result.attempts] == ["timeout", "success"]
        assert result.attempts[0]["retry"] == 1 and result.attempts[1]["fallback"]
        assert "timeout" in result.trail[0] and result.degraded
        assert calls[0]["think"] is False and calls[1]["think"] == "low"
    finally:
        await client.aclose()


async def test_timeout_exhaustion_preserves_every_attempt_and_default_is_six_seconds():
    async def handler(req):
        await asyncio.Event().wait()

    client = OllamaClient("https://ollama.test", "", transport=httpx.MockTransport(handler))
    try:
        assert LLM(client, CFG).attempt_timeout == 6
        cfg = {**CFG, "attempt_timeout_seconds": 0.01}
        with pytest.raises(LLMUnavailable) as failure:
            await LLM(client, cfg).run("turn", MESSAGES)
        assert len(failure.value.attempts) == 2
        assert all(a["outcome"] == "timeout" for a in failure.value.attempts)
        assert len(failure.value.trail) == 2
    finally:
        await client.aclose()


async def test_429_retry_and_repair_are_distinguished_without_storing_reasoning():
    count = 0

    def handler(req):
        nonlocal count
        count += 1
        if count == 1:
            return httpx.Response(429, text="PRIVATE_PROVIDER_ERROR")
        if count == 2:
            return httpx.Response(200, json={"message": {"content": "not JSON"}})
        return success()

    client = OllamaClient("https://ollama.test", "", transport=httpx.MockTransport(handler))
    try:
        result = await LLM(client, CFG, sleep=lambda _: asyncio.sleep(0)).run(
            "turn", MESSAGES, schema_model=Extraction
        )
        attempts = result.attempts
        assert [a["outcome"] for a in attempts] == ["http_error", "invalid_json", "success"]
        assert attempts[0]["status"] == 429 and attempts[0]["retry_delay_ms"] == 500
        assert [a["phase"] for a in attempts] == ["initial", "initial", "repair"]
        assert [a["retry"] for a in attempts] == [1, 2, 1]
        assert attempts[-1]["thinking_present"] and attempts[-1]["total_duration_ms"] == 100
        assert "PRIVATE" not in json.dumps(attempts) and "Leela" not in json.dumps(attempts)
    finally:
        await client.aclose()


async def test_httpx_timeout_skips_model_and_external_cancellation_does_not_fallback():
    calls = []

    async def handler(req):
        model = json.loads(req.content)["model"]
        calls.append(model)
        if model == "gpt-oss:20b":
            raise httpx.ReadTimeout("private timeout")
        return success()

    client = OllamaClient("https://ollama.test", "", transport=httpx.MockTransport(handler))
    try:
        result = await LLM(client, CFG).run("turn", MESSAGES)
        assert calls == ["gpt-oss:20b", "gemma4:31b"] and result.attempts[0]["outcome"] == "timeout"
    finally:
        await client.aclose()
    entered = asyncio.Event()
    calls = []

    async def blocking(req):
        calls.append(req)
        entered.set()
        await asyncio.Event().wait()

    client = OllamaClient("https://ollama.test", "", transport=httpx.MockTransport(blocking))
    try:
        task = asyncio.create_task(LLM(client, CFG).run("turn", MESSAGES))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert len(calls) == 1
    finally:
        await client.aclose()


def test_named_gpt_level_never_inherited_by_boolean_controlled_model():
    client = OllamaClient("https://ollama.test", "")
    gateway = LLM(client, CFG)
    assert gateway.thinking_for("gpt-oss:20b", {"think": "low"}) == "low"
    assert gateway.thinking_for("gemma4:31b", {"think": "low"}) is None
    assert gateway.thinking_for("nemotron-3-super", {"think": "medium"}) is None
    assert gateway.thinking_for("gemma4:31b", CFG["roles"]["turn"]) is False
    assert gateway.thinking_for("gemma4:31b", {"think": True}) is True
    with pytest.raises(ValueError):
        LLM(client, {**CFG, "attempt_timeout_seconds": 0})


def test_all_requested_categories_have_five_cases_and_holdout_is_disjoint():
    from scripts.extraction_metrics import counts

    root = Path(__file__).resolve().parents[1] / "evals/extraction"
    dev = [json.loads(line) for line in (root / "development.v2.jsonl").read_text().splitlines()]
    held = [json.loads(line) for line in (root / "heldout.v1.jsonl").read_text().splitlines()]
    assert all(n >= 5 for n in counts(dev).values())
    assert all(n >= 5 for n in counts(held).values())
    assert {r["id"] for r in dev}.isdisjoint(r["id"] for r in held)
    assert {r["transcript"] for r in dev}.isdisjoint(r["transcript"] for r in held)
    for row in dev + held:
        for field in row["expected_fields"]:
            assert field["evidence"] in row["transcript"]


def test_frozen_prompts_schemas_and_heldout_labels_unchanged():
    import hashlib

    root = Path(__file__).resolve().parents[2]
    frozen = json.loads((root / "artifacts/b2-followup/baseline/frozen-hashes.json").read_text())
    for name, digest in frozen.items():
        if "/graph/prompts/" in name or name.endswith("/schemas.py"):
            assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest
    folder = root / "khoj-backend/evals/extraction"
    manifest = json.loads((folder / "followup-splits.json").read_text())
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest


def test_category_language_metrics_and_empty_set_abstention():
    from scripts.extraction_metrics import breakdown, score

    row = {
        "id": "x",
        "lang": "hinglish",
        "category": "injection",
        "split": "heldout",
        "expected_fields": [],
    }
    report = breakdown([score(row, [], [])])
    assert report["by_category"]["injection_attempts"]["f1"] is None
    assert report["by_category"]["injection_attempts"]["correct_abstentions"] == 1
    assert report["by_category"]["hinglish"]["hallucination_count"] == 0
    row["expected_fields"] = [{"name": "name", "value": "Sana"}]
    result = score(row, [{"name": "age", "value": "12"}], [{"name": "age", "value": "12"}])
    assert result["fp"] == 1 and result["fn"] == 1 and breakdown([result])["overall"]["f1"] == 0
