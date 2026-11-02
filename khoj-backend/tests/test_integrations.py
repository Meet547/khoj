import asyncio
import json

import httpx

from app.integrations.gnani import Gnani, GnaniError, spell_id
from app.integrations.ollama import OllamaClient
from app.llm import LLM, LLMUnavailable
from app.privacy import redact
from app.schemas import Extraction, FieldValue, ground

CFG = {
    "privacy": {"redact_before_cloud": True},
    "roles": {"turn": {"primary": "gpt-oss:20b", "fallback": ["gemma4:31b"], "temperature": 0}},
    "language_overrides": {"hi": {"turn": "gemma4:31b"}},
}


def run(c):
    return asyncio.run(c)


def llm_with(handler):
    return LLM(
        OllamaClient("https://ollama.test", "k", transport=httpx.MockTransport(handler)),
        CFG,
        sleep=lambda s: asyncio.sleep(0),
    )


def reply(obj):
    return httpx.Response(
        200, json={"message": {"content": obj if isinstance(obj, str) else json.dumps(obj)}}
    )


def test_chain_language_override_and_fallback():
    gateway = llm_with(lambda r: reply("x"))
    assert gateway.chain("turn", "en") == ["gpt-oss:20b", "gemma4:31b"]
    assert gateway.chain("turn", "hi") == ["gemma4:31b", "gpt-oss:20b"]


def test_schema_repair_then_fallback_and_auth_header():
    seen = []

    def h(req):
        body = json.loads(req.content)
        seen.append((body["model"], req.headers["authorization"], "format" in body))
        if body["model"] == "gpt-oss:20b":
            return reply("not json")  # invalid twice -> fall back
        return reply({"intent": "provide_details", "fields": []})

    res = run(
        llm_with(h).run(
            "turn", [{"role": "user", "content": "hello"}], schema_model=Extraction, lang="en"
        )
    )
    assert res.model == "gemma4:31b" and res.parsed.intent == "provide_details"
    assert [m for m, _, _ in seen] == ["gpt-oss:20b", "gpt-oss:20b", "gemma4:31b"]
    assert all(a == "Bearer k" and f for _, a, f in seen)


def test_retry_429_then_success_and_exhaustion():
    n = {"c": 0}

    def h(req):
        n["c"] += 1
        return httpx.Response(429, text="slow down") if n["c"] < 3 else reply("ok")

    assert run(llm_with(h).run("turn", [{"role": "user", "content": "x"}])).text == "ok"
    try:
        run(
            llm_with(lambda r: httpx.Response(500, text="boom")).run(
                "turn", [{"role": "user", "content": "x"}]
            )
        )
        raise AssertionError("Expected provider failure")
    except LLMUnavailable:
        pass


def test_pii_redacted_before_cloud():
    sent = []

    def h(req):
        sent.append(json.loads(req.content)["messages"][0]["content"])
        return reply("ok")

    run(
        llm_with(h).run(
            "turn",
            [
                {
                    "role": "user",
                    "content": "Call 9876543210 or a@b.com, aadhaar 1234 5678 9012, scar on chin",
                }
            ],
        )
    )
    assert (
        "9876543210" not in sent[0]
        and "a@b.com" not in sent[0]
        and "1234 5678 9012" not in sent[0]
        and "scar on chin" in sent[0]
    )
    assert redact("age 9, 27/05/2013, 110001") == "age 9, 27/05/2013, 110001"


def test_gnani_stt_request_shape_and_parse():
    def h(req):
        assert req.url.path == "/stt/v3" and req.headers["x-api-key-id"] == "gk"
        raw = req.content
        assert b"prisma-v3.0" in raw and b"hi-IN,en-IN" in raw and b'name="audio_file"' in raw
        return httpx.Response(
            200,
            json={
                "success": True,
                "transcript": "लाल शर्ट",
                "detected_language_code": "hi-IN",
                "request_id": "r1",
            },
        )

    g = Gnani("gk", transport=httpx.MockTransport(h))
    out = run(g.transcribe(b"RIFFxxxx", ui_lang="hi"))
    assert out.transcript == "लाल शर्ट" and out.detected_language == "hi-IN" and not out.empty


def test_gnani_rate_limit_retry_and_error_mapping():
    n = {"c": 0}

    def h(req):
        n["c"] += 1
        if n["c"] < 3:
            return httpx.Response(
                429,
                json={
                    "detail": {
                        "error_code": "RATE_LIMITED",
                        "message": "one at a time",
                        "status_code": 429,
                    }
                },
            )
        return httpx.Response(200, json={"success": True, "transcript": "ok"})

    g = Gnani("gk", transport=httpx.MockTransport(h), sleep=lambda s: asyncio.sleep(0))
    assert run(g.transcribe(b"x")).transcript == "ok" and n["c"] == 3
    bad = Gnani(
        "gk",
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                400,
                json={
                    "success": False,
                    "error": {"type": "MAX_AUDIO_DURATION_EXCEEDED", "message": "30 s"},
                },
            )
        ),
    )
    try:
        run(bad.transcribe(b"x"))
        raise AssertionError("Expected provider failure")
    except GnaniError as e:
        assert e.kind == "MAX_AUDIO_DURATION_EXCEEDED" and e.status == 400


def test_gnani_tts_shape_and_json_error():
    def h(req):
        b = json.loads(req.content)
        assert (
            req.url.path == "/api/v1/tts/inference"
            and b["model"] == "timbre-v3.0"
            and b["language"] == "hi-IN"
        )
        assert b["audio_config"]["container"] == "mp3"
        return httpx.Response(200, content=b"ID3audio", headers={"content-type": "audio/mpeg"})

    assert (
        run(Gnani("gk", transport=httpx.MockTransport(h)).speak("नमस्ते", ui_lang="hi"))
        == b"ID3audio"
    )
    err = Gnani(
        "gk",
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                400,
                json={
                    "success": False,
                    "error": {"type": "INVALID_REQUEST_ERROR", "message": "bad"},
                },
            )
        ),
    )
    try:
        run(err.speak("x"))
        raise AssertionError("Expected provider failure")
    except GnaniError as e:
        assert e.kind == "INVALID_REQUEST_ERROR"
    assert spell_id("KHJ-2026-04821") == "K H J 2 0 2 6 0 4 8 2 1"


def test_grounding_drops_hallucinated_fields():
    t = "My brother Rahul is about 24. He has a scar on his left eyebrow and speaks Hindi."
    ex = Extraction(
        fields=[
            FieldValue(name="name", value="Rahul", evidence="My brother Rahul"),
            FieldValue(
                name="marks", value="scar on left eyebrow", evidence="a scar on his left eyebrow"
            ),
            FieldValue(
                name="clothing", value="blue shirt", evidence="wearing a blue shirt"
            ),  # never said
            FieldValue(name="gender", value="male", evidence=""),
        ]
    )  # no evidence
    kept, dropped = ground(t, ex)
    assert {f.name for f in kept} == {"name", "marks"} and {f.name for f in dropped} == {
        "clothing",
        "gender",
    }
