import asyncio
import copy
import io
import json
import shutil
import subprocess
import wave
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
import pytest_asyncio

from app.api.voice import get_storage
from app.core.errors import AppError
from app.core.semaphore import RedisSemaphore
from app.deps import get_current_user
from app.integrations.gnani import SLOT_WAIT_SECONDS, Gnani, tts_prepare
from app.integrations.ollama import OllamaClient
from app.integrations.storage import Storage, tts_key
from app.llm import LLM
from app.main import create_app
from app.schemas import Extraction
from app.usage import BudgetExceeded, Usage

CFG = {
    "roles": {
        "turn": {
            "primary": "primary",
            "fallback": ["backup"],
            "budget": {"calls": 1, "tokens": 10},
        },
        "compare": {"primary": "primary", "budget": {"calls": 1, "tokens": 10}},
        "explain": {"primary": "primary", "budget": {"calls": 1, "tokens": 10}},
    },
    "language_overrides": {"hi": {"turn": "indic"}},
}


def wav(seconds=1):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\0\0" * (16000 * seconds))
    return buf.getvalue()


def chat_reply(content="ok", **extra):
    return httpx.Response(200, json={"message": {"content": content}, **extra})


@pytest_asyncio.fixture
async def gateway(settings, redis, tmp_path):
    settings.tts_cache_dir = tmp_path / "tts"
    seen = {"stt": [], "tts": [], "chat": [], "tags": 0}
    behavior = {
        "stt_status": 200,
        "tts_status": 200,
        "probe_fail": False,
        "stt_text": "राहुल हिंदी बोलता है।",
        "stt_retry": 0,
    }
    cfg = settings.models()
    models = {r["primary"] for r in cfg["roles"].values()}
    for r in cfg["roles"].values():
        models.update(r.get("fallback", []))
    for overrides in cfg["language_overrides"].values():
        models.update(overrides.values())
    behavior["models"] = models

    def speech(req):
        kind = "stt" if req.url.path == "/stt/v3" else "tts"
        seen[kind].append(req.content)
        status = behavior[f"{kind}_status"]
        if kind == "stt" and len(seen[kind]) <= behavior["stt_retry"]:
            status = 429
        if status != 200:
            return httpx.Response(status, json={"error": {"message": "PRIVATE_PROVIDER_DETAIL"}})
        if kind == "stt":
            return httpx.Response(
                200, json={"transcript": behavior["stt_text"], "detected_language_code": "hi-IN"}
            )
        return httpx.Response(200, content=b"ID3fake-mp3", headers={"content-type": "audio/mpeg"})

    def models_handler(req):
        if req.url.path == "/api/tags":
            seen["tags"] += 1
            if behavior["probe_fail"]:
                return httpx.Response(503)
            return httpx.Response(200, json={"models": [{"name": m} for m in behavior["models"]]})
        seen["chat"].append(json.loads(req.content))
        return chat_reply(
            json.dumps(
                {
                    "intent": "provide_details",
                    "fields": [
                        {"name": "name", "value": "Rahul", "evidence": "राहुल"},
                        {"name": "clothing", "value": "blue shirt", "evidence": "नीली कमीज़"},
                    ],
                }
            ),
            eval_count=5,
            prompt_eval_count=7,
        )

    gnani = Gnani(
        "test",
        transport=httpx.MockTransport(speech),
        shared_stt=RedisSemaphore(redis, "test:stt", 1),
        sleep=lambda _: asyncio.sleep(0),
    )
    ollama = OllamaClient(
        "https://ollama.test", "test", transport=httpx.MockTransport(models_handler)
    )
    app = create_app(settings, redis=redis, gnani=gnani, ollama=ollama)
    app.dependency_overrides[get_current_user] = lambda: None
    try:
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app), base_url="https://testserver"
            ) as client:
                yield SimpleNamespace(
                    app=app, client=client, seen=seen, behavior=behavior, settings=settings
                )
    finally:
        await gnani.aclose()
        await ollama.aclose()


async def test_stt_auto_topic_empty_and_size(gateway):
    g = gateway
    response = await g.client.post(
        "/api/voice/stt",
        files={"audio": ("voice.wav", wav())},
        data={"lang": "auto", "topic": "missing person"},
    )
    assert response.json() == {
        "transcript": "राहुल हिंदी बोलता है।",
        "detectedLang": "hi-IN",
        "empty": False,
    }
    assert b"indic-auto" in g.seen["stt"][0] and b"missing person" in g.seen["stt"][0]
    g.behavior["stt_text"] = "  "
    response = await g.client.post("/api/voice/stt", files={"audio": ("voice.wav", wav())})
    assert response.json()["empty"] is True
    count = len(g.seen["stt"])
    response = await g.client.post(
        "/api/voice/stt", files={"audio": ("huge.wav", b"0" * (2 * 1024 * 1024 + 1))}
    )
    assert response.status_code == 413 and response.json()["error"]["retryable"] is False
    assert len(g.seen["stt"]) == count


@pytest.mark.parametrize("data,message", [(wav(31), "30 seconds"), (b"garbage", "decode audio")])
async def test_stt_rejects_invalid_duration_before_provider(gateway, data, message):
    response = await gateway.client.post("/api/voice/stt", files={"audio": ("clip.wav", data)})
    assert response.status_code == 422 and response.json()["error"]["retryable"] is False
    assert message in response.json()["error"]["message"]
    assert not gateway.seen["stt"]


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg required")
async def test_webm_upload_is_converted_before_stt(gateway):
    audio = (
        await asyncio.to_thread(
            subprocess.run,
            [
                "ffmpeg",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=1",
                "-f",
                "webm",
                "pipe:1",
            ],
            capture_output=True,
            check=True,
        )
    ).stdout
    response = await gateway.client.post(
        "/api/voice/stt", files={"audio": ("clip.webm", audio, "audio/webm")}, data={"lang": "hi"}
    )
    assert response.status_code == 200
    sent = gateway.seen["stt"][0]
    assert b"RIFF" in sent and b'filename="speech.wav"' in sent and b"hi-IN,en-IN" in sent


async def test_stt_429_retries_then_success(gateway):
    gateway.behavior["stt_retry"] = 2
    response = await gateway.client.post("/api/voice/stt", files={"audio": ("clip.wav", wav())})
    assert response.status_code == 200 and len(gateway.seen["stt"]) == 3


@pytest.mark.parametrize(
    "status,expected,retry",
    [(429, 429, True), (503, 503, True), (403, 503, False), (400, 422, False)],
)
@pytest.mark.parametrize("kind", ["stt", "tts"])
async def test_voice_provider_errors_are_safe(gateway, status, expected, retry, kind):
    gateway.behavior[f"{kind}_status"] = status
    kwargs = (
        {"files": {"audio": ("clip.wav", wav())}}
        if kind == "stt"
        else {"json": {"text": "नमस्ते", "lang": "hi"}}
    )
    response = await gateway.client.post(f"/api/voice/{kind}", **kwargs)
    assert response.status_code == expected and response.json()["error"]["retryable"] is retry
    assert "PRIVATE_PROVIDER_DETAIL" not in response.text
    if status == 429:
        assert response.json()["error"]["code"] == "busy" and response.headers["retry-after"] == "1"


async def test_tts_cache_hit_skips_gnani_and_signed_url_works(gateway):
    g = gateway
    body = {"text": "केस KHJ-2026-04821 और ११", "lang": "hi"}
    response = await g.client.post("/api/voice/tts", json=body)
    assert response.status_code == 200 and response.content == b"ID3fake-mp3"
    assert response.headers["content-type"].startswith("audio/mpeg")
    assert response.headers["x-tts-cache"] == "miss"
    cached = await g.client.post("/api/voice/tts", json=body)
    assert cached.content == response.content and cached.headers["x-tts-cache"] == "hit"
    assert len(g.seen["tts"]) == 1
    request = json.loads(g.seen["tts"][0])
    assert (
        "K H J" in request["text"]
        and "शून्य चार आठ दो एक" in request["text"]
        and "एक एक" in request["text"]
    )
    url = cached.headers["x-audio-url"]
    assert (await g.client.get(url)).content == cached.content
    assert (await g.client.get(url.replace("signature=", "signature=bad"))).status_code == 403
    expires = parse_qs(urlsplit(url).query)["expires"][0]
    assert (await g.client.get(url.replace(f"expires={expires}", "expires=0"))).status_code == 403
    files = list(g.settings.tts_cache_dir.iterdir())
    assert len(files) == 1 and files[0].stat().st_mode & 0o777 == 0o600
    assert "केस" not in files[0].name


async def test_voice_validation_never_calls_provider(gateway):
    for body in [{"text": " "}, {"text": "x", "lang": "xx"}, {"text": "x" * 5001}]:
        assert (await gateway.client.post("/api/voice/tts", json=body)).status_code == 422
    assert (
        await gateway.client.post(
            "/api/voice/stt", files={"audio": ("x", wav())}, data={"lang": "xx"}
        )
    ).status_code == 422
    assert not gateway.seen["stt"] and not gateway.seen["tts"]


def test_cache_key_includes_every_parameter_and_spells_ids():
    args = ["text", "hi", "Shivani", "timbre-v3.0", 1.0]
    keys = {tts_key(*args)}
    for i, value in enumerate(["other", "en", "Avinash", "timbre-v2.5", 0.9]):
        variant = args.copy()
        variant[i] = value
        keys.add(tts_key(*variant))
    assert len(keys) == 6
    assert (
        tts_prepare("Case KHJ-2026-001 and 1100", "en")
        == "Case K H J two zero two six zero zero one and one one zero zero"
    )
    assert tts_prepare("नमस्ते", "hi") == "नमस्ते"


async def test_turn_is_grounded_redacted_and_has_usage(gateway):
    response = await gateway.client.post(
        "/api/llm/turn", json={"transcript": "राहुल हिंदी बोलता है। 9876543210", "lang": "hi"}
    )
    result = response.json()
    assert response.status_code == 200 and result["model"] == "gemma4:31b"
    assert (
        result["fields"] == [{"name": "name", "value": "Rahul", "evidence": "राहुल"}]
        and result["dropped"] == 1
    )
    assert "9876543210" not in json.dumps(gateway.seen["chat"])
    usage = await gateway.app.state.usage.snapshot()
    assert usage["roles"]["turn"]["calls"] == 1 and usage["roles"]["turn"]["tokens"] == 12


@pytest.mark.parametrize(
    "role,status", [(None, 401), ("citizen", 403), ("officer", 403), ("admin", 200)]
)
async def test_admin_health_and_usage_are_admin_only(gateway, role, status):
    gateway.app.dependency_overrides[get_current_user] = lambda: (
        SimpleNamespace(role=role) if role else None
    )
    count = gateway.seen["tags"]
    for path in ["/api/admin/usage", "/api/admin/health"]:
        assert (await gateway.client.get(path)).status_code == status
    assert gateway.seen["tags"] == count + int(role == "admin")


async def test_probe_missing_primary_fallback_and_override_are_exposed(gateway):
    assert gateway.seen["tags"] == 1 and not gateway.app.state.capabilities.report["degraded"]
    gateway.behavior["models"].remove("gpt-oss:20b")
    gateway.behavior["models"].remove("gemma4:31b")
    gateway.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="admin")
    response = await gateway.client.get("/api/admin/health")
    report = response.json()["ollama"]
    assert report["roles"]["turn"]["primaryMissing"] and report["roles"]["turn"]["degraded"]
    assert "gemma4:31b" in report["roles"]["turn"]["missing"]
    result = (await gateway.client.post("/api/llm/turn", json={"transcript": "राहुल"})).json()
    assert result["model"] == "gpt-oss:120b" and result["degraded"]


async def test_probe_failure_does_not_crash_and_recovers(gateway):
    gateway.behavior["probe_fail"] = True
    report = await gateway.app.state.capabilities.probe()
    assert report["degraded"] and report["error"] == "ollama_unavailable"
    assert (
        await gateway.client.post("/api/llm/turn", json={"transcript": "राहुल"})
    ).status_code == 200
    gateway.behavior["probe_fail"] = False
    assert not (await gateway.app.state.capabilities.probe())["degraded"]


async def test_startup_survives_real_probe_exception(settings, redis):
    async def fail(req):
        raise httpx.ConnectError("PRIVATE_URL")

    client = OllamaClient("https://ollama.test", "", transport=httpx.MockTransport(fail))
    try:
        app = create_app(settings, redis=redis, ollama=client)
        async with app.router.lifespan_context(app):
            assert app.state.capabilities.report["error"] == "ollama_unavailable"
    finally:
        await client.aclose()


@pytest.mark.parametrize("role", ["compare", "explain"])
@pytest.mark.parametrize("limit", ["calls", "tokens"])
async def test_optional_roles_skip_at_daily_budget(redis, role, limit):
    cfg = copy.deepcopy(CFG)
    cfg["roles"][role]["budget"] = {limit: 1}
    seen = []

    def handler(req):
        seen.append(req)
        return chat_reply(eval_count=1)

    client = OllamaClient("https://ollama.test", "", transport=httpx.MockTransport(handler))
    usage = Usage(redis, cfg)
    llm = LLM(client, cfg, usage=usage)
    try:
        first = await llm.run(role, [{"role": "user", "content": "x"}])
        second = await llm.run(role, [{"role": "user", "content": "x"}])
        assert first.degraded and second.degraded and second.skipped and len(seen) == 1
        assert (await usage.snapshot())["roles"][role]["disabled"]
    finally:
        await client.aclose()


async def test_budgets_count_retries_repairs_and_essential_roles_continue(redis):
    calls = 0

    def handler(req):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429)
        return chat_reply(
            "bad json" if calls == 2 else '{"intent":"help","fields":[]}',
            eval_count=2,
            prompt_eval_count=3,
        )

    client = OllamaClient("https://ollama.test", "", transport=httpx.MockTransport(handler))
    usage = Usage(redis, CFG)
    llm = LLM(client, CFG, usage=usage, sleep=lambda _: asyncio.sleep(0))
    try:
        result = await llm.run("turn", [{"role": "user", "content": "x"}], schema_model=Extraction)
        assert result.degraded and not result.skipped
        state = (await usage.snapshot())["roles"]["turn"]
        assert state["calls"] == 3 and state["tokens"] == 10 and not state["disabled"]
        assert 0 < await redis.ttl(usage.key("turn", usage.day())) <= 172800
    finally:
        await client.aclose()


async def test_budget_reservation_is_atomic_across_instances_and_resets_daily(redis, monkeypatch):
    a, b = Usage(redis, CFG), Usage(redis, CFG)
    results = await asyncio.gather(
        a.reserve("compare"), b.reserve("compare"), return_exceptions=True
    )
    assert sum(isinstance(r, BudgetExceeded) for r in results) == 1
    monkeypatch.setattr(b, "day", lambda: "2099-01-02")
    assert await b.reserve("compare") == "2099-01-02"


async def test_explicit_disabled_role_skips_transport(redis):
    cfg = copy.deepcopy(CFG)
    cfg["roles"]["compare"]["enabled"] = False
    client = OllamaClient(
        "https://ollama.test",
        "",
        transport=httpx.MockTransport(lambda _: pytest.fail("called disabled role")),
    )
    try:
        assert (await LLM(client, cfg, usage=Usage(redis, cfg)).run("compare", [])).skipped
    finally:
        await client.aclose()


async def test_shared_stt_limit_across_clients_and_releases_on_cancellation(redis):
    active, peak = 0, 0
    entered, release = asyncio.Event(), asyncio.Event()

    async def handler(req):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        entered.set()
        try:
            await release.wait()
            return httpx.Response(200, json={"transcript": "ok"})
        finally:
            active -= 1

    a, b = [
        Gnani(
            "key",
            transport=httpx.MockTransport(handler),
            shared_stt=RedisSemaphore(redis, "shared", 1),
        )
        for _ in range(2)
    ]
    try:
        first = asyncio.create_task(a.transcribe(b"x"))
        await entered.wait()
        second = asyncio.create_task(b.transcribe(b"x"))
        await asyncio.sleep(0.07)
        assert peak == 1 and not second.done()
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        release.set()
        assert (await second).transcript == "ok" and peak == 1
        assert await redis.zcard("shared") == 0
    finally:
        await a.aclose()
        await b.aclose()


async def test_stt_busy_after_bounded_wait_and_crashed_lease_expires(redis, monkeypatch):
    assert SLOT_WAIT_SECONDS == 8
    monkeypatch.setattr("app.integrations.gnani.SLOT_WAIT_SECONDS", 0.02)
    await redis.zadd("shared", {"live-worker": 9999999999})
    client = Gnani(
        "key",
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"transcript": "ok"})),
        shared_stt=RedisSemaphore(redis, "shared", 1),
    )
    try:
        with pytest.raises(AppError) as error:
            await client.transcribe(b"x")
        assert error.value.code == "busy" and error.value.status == 429 and error.value.retryable
        await redis.zadd("shared", {"live-worker": 0})
        assert (await client.transcribe(b"x")).transcript == "ok"
        assert await redis.zcard("shared") == 0
    finally:
        await client.aclose()


async def test_local_queue_wait_is_bounded(redis, monkeypatch):
    monkeypatch.setattr("app.integrations.gnani.SLOT_WAIT_SECONDS", 0.02)
    client = Gnani("key")
    await client._stt.acquire()
    try:
        with pytest.raises(AppError) as error:
            await client.transcribe(b"x")
        assert error.value.code == "busy"
    finally:
        client._stt.release()
        await client.aclose()


async def test_r2_transport_cache_and_presigned_urls(settings):
    settings.r2_endpoint = "https://account.r2.cloudflarestorage.com"
    from pydantic import SecretStr

    settings.r2_access_key_id = SecretStr("public-test-key")
    settings.r2_secret_access_key = SecretStr("private-test-key")
    objects = {}

    def handler(req):
        query = parse_qs(urlsplit(str(req.url)).query)
        assert query["X-Amz-Algorithm"] == ["AWS4-HMAC-SHA256"]
        assert len(query["X-Amz-Signature"][0]) == 64
        assert "auto/s3/aws4_request" in query["X-Amz-Credential"][0]
        if req.method == "PUT":
            assert req.headers["content-type"] == "audio/mpeg"
            objects[req.url.path] = req.content
            return httpx.Response(200)
        return (
            httpx.Response(200, content=objects[req.url.path])
            if req.url.path in objects
            else httpx.Response(404)
        )

    storage = Storage(settings, httpx.MockTransport(handler))
    key = tts_key("text", "hi", "voice", "model", 1.0)
    try:
        assert await storage.get(key) is None
        await storage.put(key, b"mp3")
        assert await storage.get(key) == b"mp3"
        assert storage.signed_url(key).startswith(settings.r2_endpoint)
        with pytest.raises(AppError):
            await storage.get("../escape")
    finally:
        await storage.aclose()


def test_production_cannot_fall_back_to_disk(settings):
    settings.env = "production"
    with pytest.raises(ValueError, match="R2 must"):
        Storage(settings)


@pytest.mark.parametrize("kind", ["stt", "tts"])
async def test_voice_transport_outages_are_retryable(gateway, kind, monkeypatch):
    async def fail(*args, **kwargs):
        raise httpx.ConnectError("PRIVATE_PROVIDER_URL")

    monkeypatch.setattr(gateway.app.state.gnani._c, "post", fail)
    kwargs = (
        {"files": {"audio": ("clip.wav", wav())}} if kind == "stt" else {"json": {"text": "नमस्ते"}}
    )
    response = await gateway.client.post(f"/api/voice/{kind}", **kwargs)
    assert response.status_code == 503 and response.json()["error"]["retryable"]
    assert "PRIVATE" not in response.text


async def test_stt_redis_failure_is_closed_and_releases_local_slot(gateway, monkeypatch):
    from redis.exceptions import ConnectionError

    async def fail(*args):
        raise ConnectionError("PRIVATE_REDIS_URL")

    monkeypatch.setattr(gateway.app.state.gnani.shared_stt.redis, "eval", fail)
    response = await gateway.client.post("/api/voice/stt", files={"audio": ("clip.wav", wav())})
    assert response.status_code == 503 and response.json()["error"]["retryable"]
    assert not gateway.app.state.gnani._stt.locked() and not gateway.seen["stt"]


async def test_r2_cache_hit_skips_synthesis_and_cache_outage_is_retryable(gateway):
    from pydantic import SecretStr

    settings = gateway.settings.model_copy(
        update={
            "r2_endpoint": "https://account.r2.cloudflarestorage.com",
            "r2_access_key_id": SecretStr("test-key"),
            "r2_secret_access_key": SecretStr("test-secret"),
        }
    )
    status = 200

    def handler(req):
        return httpx.Response(status, content=b"cached-r2-audio")

    storage = Storage(settings, httpx.MockTransport(handler))
    gateway.app.dependency_overrides[get_storage] = lambda: storage
    try:
        response = await gateway.client.post("/api/voice/tts", json={"text": "नमस्ते"})
        assert response.content == b"cached-r2-audio" and response.headers["x-tts-cache"] == "hit"
        assert response.headers["x-audio-url"].startswith(settings.r2_endpoint)
        assert not gateway.seen["tts"]
        status = 503
        response = await gateway.client.post("/api/voice/tts", json={"text": "नमस्ते"})
        assert response.status_code == 503 and response.json()["error"]["retryable"]
        assert not gateway.seen["tts"]
    finally:
        await storage.aclose()


async def test_turn_missing_all_models_returns_retryable_error(gateway):
    gateway.behavior["models"] = set()
    await gateway.app.state.capabilities.probe()
    response = await gateway.client.post("/api/llm/turn", json={"transcript": "राहुल"})
    assert response.status_code == 503 and response.json()["error"]["retryable"]
    assert not gateway.seen["chat"]
