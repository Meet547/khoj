import asyncio
from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.core.security import PhoneVault
from app.db.models import User

pytestmark = pytest.mark.integration


async def login(client, phone="9000000001"):
    send = await client.post("/api/auth/otp/send", json={"phone": phone})
    assert send.status_code == 200 and send.json() == {"ok": True, "demo": True}
    return await client.post("/api/auth/otp/verify", json={"phone": phone, "code": "123456"})


async def test_demo_login_cookie_contract_and_encrypted_storage(client, database, settings):
    response = await login(client)
    assert response.status_code == 200
    user = response.json()["user"]
    assert set(user) == {"id", "role", "lang"} and user["role"] == "citizen"
    cookies = response.headers.get_list("set-cookie")
    assert len(cookies) == 2
    assert all(
        "HttpOnly" in value and "Secure" in value and "SameSite=lax" in value for value in cookies
    )
    assert "Max-Age=900" in cookies[0]
    assert (await client.get("/api/auth/me")).json()["user"] == user
    async with database() as db:
        stored = await db.get(User, UUID(user["id"]))
        vault = PhoneVault(settings)
        assert stored.phone_hash == vault.digest("9000000001")
        assert vault.decrypt(stored.phone_enc) == "9000000001"
        assert stored.phone_enc != b"9000000001"


@pytest.mark.parametrize(
    "phone,role",
    [
        ("9000000001", "citizen"),
        ("9000000002", "volunteer"),
        ("9000000003", "officer"),
        ("9000000004", "admin"),
        ("9876543210", "citizen"),
    ],
)
async def test_demo_role_accounts(client, phone, role):
    assert (await login(client, phone)).json()["user"]["role"] == role


async def test_no_code_before_send_and_wrong_code(client):
    body = {"phone": "9000000001", "code": "123456"}
    assert (await client.post("/api/auth/otp/verify", json=body)).status_code == 400
    await client.post("/api/auth/otp/send", json={"phone": body["phone"]})
    body["code"] = "000000"
    response = await client.post("/api/auth/otp/verify", json=body)
    assert response.status_code == 400 and response.json()["error"]["code"] == "invalid_code"
    assert not response.headers.get_list("set-cookie")


@pytest.mark.parametrize(
    "phone", ["1234567890", "900000000", "90000000011", "+919000000001", "not a phone"]
)
async def test_invalid_phone_error_does_not_echo_input(client, phone):
    response = await client.post("/api/auth/otp/send", json={"phone": phone})
    assert response.status_code == 422
    assert phone not in response.text
    assert set(response.json()["error"]) == {"code", "message", "retryable"}


async def test_send_and_verify_limits(client):
    for _ in range(5):
        assert (
            await client.post("/api/auth/otp/send", json={"phone": "9000000001"})
        ).status_code == 200
    response = await client.post("/api/auth/otp/send", json={"phone": "9000000001"})
    assert response.status_code == 429 and int(response.headers["retry-after"]) > 0
    for _ in range(10):
        assert (
            await client.post(
                "/api/auth/otp/verify", json={"phone": "9000000001", "code": "000000"}
            )
        ).status_code == 400
    assert (
        await client.post("/api/auth/otp/verify", json={"phone": "9000000001", "code": "000000"})
    ).status_code == 429


async def test_per_ip_send_limit_cannot_be_bypassed_by_spoofing(client):
    for index in range(50):
        response = await client.post(
            "/api/auth/otp/send",
            json={"phone": str(9100000000 + index)},
            headers={"X-Forwarded-For": f"1.2.3.{index}"},
        )
        assert response.status_code == 200
    assert (
        await client.post("/api/auth/otp/send", json={"phone": "9200000000"})
    ).status_code == 429


async def test_refresh_rotation_and_replay_revokes_entire_session(client):
    assert (await login(client)).status_code == 200
    original = client.cookies.get("khoj_refresh")
    assert (await client.post("/api/auth/refresh")).status_code == 200
    assert original != client.cookies.get("khoj_refresh")
    assert (await client.get("/api/auth/me")).status_code == 200
    # Replay the consumed token. The current access token must be invalid immediately.
    response = await client.post(
        "/api/auth/refresh", headers={"Cookie": f"khoj_refresh={original}"}
    )
    assert response.status_code == 401
    assert (await client.get("/api/auth/me")).status_code == 401
    assert (await client.post("/api/auth/refresh")).status_code == 401


async def test_otp_redemption_is_single_use_under_concurrency(client, database):
    await client.post("/api/auth/otp/send", json={"phone": "9000000001"})
    responses = await asyncio.gather(
        *(
            client.post("/api/auth/otp/verify", json={"phone": "9000000001", "code": "123456"})
            for _ in range(2)
        )
    )
    assert sorted(response.status_code for response in responses) == [200, 400]
    async with database() as db:
        assert await db.scalar(select(func.count()).select_from(User)) == 1


async def test_logout_revokes_copied_access_token(client):
    await login(client)
    copied = client.cookies.get("khoj_session")
    assert (await client.post("/api/auth/logout")).status_code == 204
    assert not client.cookies
    response = await client.get("/api/auth/me", headers={"Cookie": f"khoj_session={copied}"})
    assert response.status_code == 401
    assert (await client.post("/api/auth/logout")).status_code == 204


async def test_csrf_and_correlation_header(client):
    response = await client.post(
        "/api/auth/otp/send",
        json={"phone": "9000000001"},
        headers={"Origin": "https://attacker.example"},
    )
    assert response.status_code == 403
    response = await client.get("/api/health", headers={"X-Request-ID": "test_request-123"})
    assert response.status_code == 200
    assert response.json() == {"ok": True, "checks": {"database": True, "redis": True}}
    assert response.headers["X-Request-ID"] == "test_request-123"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


async def test_prototype_routes_remain_private(client):
    for path in ("/", "/api/search", "/docs", "/openapi.json"):
        response = await client.get(path)
        assert response.status_code == 404
    assert (await client.get("/api/auth/me")).status_code == 401
