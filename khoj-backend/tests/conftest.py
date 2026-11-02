import os
import subprocess
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from fakeredis.aioredis import FakeRedis
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import Settings
from app.db.models import Base
from app.integrations.ollama import OllamaClient
from app.main import create_app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings():
    return Settings(env="test", _env_file=None)


@pytest.fixture(scope="session")
def migrated_database():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a disposable PostgreSQL database")
    from sqlalchemy.engine import make_url

    assert make_url(url).database.endswith("_test"), "Integration database must end with _test"
    env = {**os.environ, "KHOJ_ENV": "test", "DATABASE_URL": url}

    def migrate(revision):
        subprocess.run(
            [str(ROOT / ".venv/bin/alembic"), *revision],
            cwd=ROOT,
            env=env,
            check=True,
            capture_output=True,
        )

    migrate(["upgrade", "head"])
    migrate(["downgrade", "base"])
    # Check downgrade removed every application table and view, then re-apply from empty.
    import asyncio

    async def assert_empty():
        engine = create_async_engine(url, poolclass=NullPool)
        try:
            async with engine.connect() as db:
                tables = (
                    (
                        await db.execute(
                            text(
                                "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename != 'alembic_version'"
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                assert tables == []
        finally:
            await engine.dispose()

    asyncio.run(assert_empty())
    migrate(["upgrade", "head"])
    return url


@pytest_asyncio.fixture
async def database(migrated_database):
    engine = create_async_engine(migrated_database, poolclass=NullPool, hide_parameters=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        tables = ", ".join(
            '"' + name + '"'
            for name in [
                *Base.metadata.tables,
                "checkpoints",
                "checkpoint_blobs",
                "checkpoint_writes",
            ]
        )
        await conn.execute(text("TRUNCATE " + tables + " RESTART IDENTITY CASCADE"))
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def redis():
    url = os.getenv("TEST_REDIS_URL")
    if url:
        assert url.rsplit("/", 1)[-1] == "15", "Only Redis database 15 may be cleared by tests"
        client = Redis.from_url(url)
    else:
        client = FakeRedis()
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()


@pytest_asyncio.fixture
async def client(settings, database, redis):
    ollama = OllamaClient(
        "https://ollama.test",
        "",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"models": []})),
    )
    try:
        app = create_app(settings, db_factory=database, redis=redis, ollama=ollama)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="https://testserver"
            ) as http:
                yield http
    finally:
        await ollama.aclose()
