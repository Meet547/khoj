import asyncio
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
import yaml
from redis.exceptions import ConnectionError
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.api.health import health
from app.config import Settings
from app.core.errors import AppError
from app.core.rate_limit import RateLimiter
from app.db.models import GazetteerPlace, ScoringVersion, User
from app.integrations.sms import UnconfiguredOtpProvider

ROOT = Path(__file__).resolve().parents[1]


def test_env_initializer_never_overwrites_and_uses_private_permissions(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/init_env.py")], cwd=tmp_path, capture_output=True
    )
    assert result.returncode == 0, result.stderr
    env = tmp_path / ".env"
    assert env.stat().st_mode & 0o777 == 0o600
    original = env.read_bytes()
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/init_env.py")], cwd=tmp_path, capture_output=True
    )
    assert result.returncode != 0 and env.read_bytes() == original
    settings = Settings(env="development", _env_file=env)
    assert settings.env == "development"
    assert settings.jwt_secret.get_secret_value().encode() not in result.stdout


def test_compose_structure_and_credential_separation():
    config = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    services = config["services"]
    assert set(services) == {"api", "worker", "postgres", "redis", "migrate"}
    assert "khoj_app:" in services["api"]["environment"]["DATABASE_URL"]
    assert "khoj:khoj@" in services["migrate"]["environment"]["DATABASE_URL"]
    assert services["api"]["depends_on"]["migrate"]["condition"] == "service_completed_successfully"
    assert services["api"]["ports"] == ["127.0.0.1:8000:8000"]


async def test_real_otp_fails_closed_until_a_provider_is_configured():
    provider = UnconfiguredOtpProvider()
    assert provider.demo is False
    with pytest.raises(AppError) as error:
        await provider.send("9000000003")
    assert error.value.status == 503
    with pytest.raises(AppError):
        await provider.verify("9000000003", "123456")


async def test_redis_outage_fails_closed():
    class BrokenRedis:
        async def eval(self, *args):
            raise ConnectionError("private backend URL must not leak")

    with pytest.raises(AppError) as error:
        await RateLimiter(BrokenRedis()).check("test", 5)
    assert error.value.status == 503 and error.value.retryable
    assert "private" not in error.value.message


@pytest.mark.integration
async def test_seed_is_idempotent(database, migrated_database):
    env = {**os.environ, "KHOJ_ENV": "test", "DEMO_AUTH": "1", "DATABASE_URL": migrated_database}
    # Fixed test-only keys ensure separate seed processes compute identical lookup hashes.
    env["PHONE_HMAC_SECRET"] = "test-phone-hmac-secret-at-least-32-characters"
    for _ in range(2):
        result = await asyncio.to_thread(
            subprocess.run,
            [sys.executable, "-m", "scripts.seed"],
            cwd=ROOT,
            env=env,
            capture_output=True,
        )
        assert result.returncode == 0, result.stderr
    async with database() as db:
        assert await db.scalar(select(func.count()).select_from(User)) == 4
        assert await db.scalar(select(func.count()).select_from(ScoringVersion)) == 1
        assert await db.scalar(select(func.count()).select_from(GazetteerPlace)) == 1


@pytest.mark.integration
async def test_runtime_role_cannot_create_or_drop_tables(database, migrated_database):
    from sqlalchemy.engine import make_url
    from sqlalchemy.exc import DBAPIError

    role = "khoj_test_app_" + uuid4().hex[:12]
    async with database() as db:
        await db.execute(
            text(
                f"CREATE ROLE \"{role}\" LOGIN PASSWORD 'test-role-only-password' NOSUPERUSER NOCREATEDB NOCREATEROLE"
            )
        )
        await db.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role}"'))
        await db.execute(
            text(f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "{role}"')
        )
        await db.execute(text("REVOKE CREATE ON SCHEMA public FROM PUBLIC"))
        await db.commit()
    engine = create_async_engine(
        make_url(migrated_database).set(username=role, password="test-role-only-password"),
        poolclass=NullPool,
    )
    try:
        async with engine.connect() as conn:
            assert (await conn.execute(text("SELECT count(*) FROM users"))).scalar_one() == 0
            await conn.rollback()
            with pytest.raises(DBAPIError):
                await conn.execute(text("CREATE TABLE should_not_exist (id int)"))
            await conn.rollback()
            with pytest.raises(DBAPIError):
                await conn.execute(text("DROP TABLE users"))
            await conn.rollback()
    finally:
        await engine.dispose()
        async with database() as db:
            await db.execute(text(f'DROP OWNED BY "{role}"'))
            await db.execute(text(f'DROP ROLE "{role}"'))
            await db.commit()


async def test_health_reports_dependency_outages_without_leaking_errors():
    import json

    class BrokenDatabase:
        async def execute(self, statement):
            raise OSError("private connection details")

        async def rollback(self):
            pass

    class BrokenRedis:
        async def ping(self):
            raise ConnectionError("private redis credentials")

    response = await health(BrokenDatabase(), BrokenRedis())
    assert response.status_code == 503
    assert json.loads(response.body) == {"ok": False, "checks": {"database": False, "redis": False}}
    assert b"private" not in response.body
