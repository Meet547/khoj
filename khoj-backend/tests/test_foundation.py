import asyncio
import base64
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from cryptography.exceptions import InvalidTag
from pydantic import ValidationError
from sqlalchemy import select, text

from app.config import Settings
from app.core.audit import Actor
from app.core.errors import AppError
from app.core.ids import next_case_number
from app.core.logging import JsonFormatter
from app.core.rate_limit import RateLimiter
from app.core.security import PhoneVault, decode_access, issue_access
from app.db.models import AuditLog, Base, Person, User
from app.db.repo.persons import PersonRepository
from app.deps import require_role


def test_production_demo_is_rejected():
    with pytest.raises(ValidationError, match="DEMO_AUTH must be off"):
        Settings(env="production", demo_auth=True, _env_file=None)


def test_non_test_settings_require_explicit_stable_secrets():
    with pytest.raises(ValidationError, match="Set JWT_SECRET"):
        Settings(env="development", _env_file=None)


def test_bad_encryption_keys_and_weak_secrets_rejected():
    with pytest.raises(ValidationError, match="32 bytes"):
        Settings(
            env="test",
            phone_enc_key=base64.urlsafe_b64encode(b"too-short").decode(),
            _env_file=None,
        )
    with pytest.raises(ValidationError, match="32 characters"):
        Settings(env="test", jwt_secret="short", _env_file=None)


def test_phone_encryption_round_trip_and_tamper(settings):
    vault = PhoneVault(settings)
    phone = "9876543210"
    first, second = vault.encrypt(phone), vault.encrypt(phone)
    assert first != second and phone.encode() not in first
    assert vault.decrypt(first) == phone
    assert vault.digest(phone) == vault.digest(phone)
    assert vault.digest(phone) != vault.digest("9876543211")
    with pytest.raises(InvalidTag):
        vault.decrypt(first[:-1] + bytes([first[-1] ^ 1]))


def test_access_token_has_no_pii_and_rejects_tampering(settings):
    user_id, session_id = uuid4(), uuid4()
    token = issue_access(settings, user_id, "citizen", session_id)
    assert decode_access(settings, token) == (user_id, "citizen", session_id)
    claims = jwt.decode(
        token, settings.jwt_secret.get_secret_value(), algorithms=["HS256"], audience="khoj-web"
    )
    assert set(claims) == {"sub", "role", "jti", "iat", "exp", "iss", "aud"}
    assert claims["exp"] - claims["iat"] == 900
    with pytest.raises(AppError):
        decode_access(settings, token + "bad")
    expired = {**claims, "exp": datetime.now(UTC) - timedelta(seconds=1)}
    with pytest.raises(AppError):
        decode_access(
            settings, jwt.encode(expired, settings.jwt_secret.get_secret_value(), algorithm="HS256")
        )


async def test_role_guard():
    guard = require_role("officer")
    officer = User(id=uuid4(), role="officer")
    citizen = User(id=uuid4(), role="citizen")
    assert await guard(officer) is officer
    with pytest.raises(AppError) as exc:
        await guard(citizen)
    assert exc.value.status == 403


async def test_redis_limiter_atomic_and_expiring(redis):
    limiter = RateLimiter(redis)
    results = await asyncio.gather(
        *(limiter.check("concurrent", 5) for _ in range(12)), return_exceptions=True
    )
    assert sum(result is None for result in results) == 5
    errors = [result for result in results if isinstance(result, AppError)]
    assert len(errors) == 7 and all(error.status == 429 for error in errors)
    assert 0 < await redis.ttl("rate:concurrent") <= 3600


@pytest.mark.integration
async def test_migration_schema_and_orm_agree(database):
    async with database() as db:
        connection = await db.connection()

        def compare(sync):
            return compare_metadata(
                MigrationContext.configure(
                    sync,
                    opts={
                        "include_object": lambda obj, name, type_, reflected, compare_to: (
                            not (type_ == "table" and name.startswith("checkpoint"))
                        )
                    },
                ),
                Base.metadata,
            )

        changes = await connection.run_sync(compare)
        # Views and explicit standalone sequences are outside ORM table metadata.
        assert changes == []
        extensions = (await db.execute(text("SELECT extname FROM pg_extension"))).scalars().all()
        assert {"pgcrypto", "pg_trgm"} <= set(extensions)
        assert (await db.execute(text("SELECT count(*) FROM citizen_persons"))).scalar_one() == 0


@pytest.mark.integration
async def test_case_number_unique_under_concurrency(database):
    async def generate():
        async with database() as db, db.begin():
            return await next_case_number(db)

    values = await asyncio.gather(*(generate() for _ in range(25)))
    assert len(set(values)) == 25
    import re

    assert all(re.fullmatch(r"KHJ-\d{4}-\d{5,}", value) for value in values)


@pytest.mark.integration
async def test_restricted_reads_are_durable_and_roles_filter(database):
    officer_id = uuid4()
    async with database() as db, db.begin():
        public = Person(origin="test", kind="missing", access_class="public_summary")
        restricted = Person(origin="test", kind="found", access_class="restricted")
        body = Person(origin="test", kind="unidentified_body", access_class="officer_only")
        public_found = Person(origin="test", kind="found", access_class="public_summary")
        db.add_all([public, restricted, body, public_found])
        await db.flush()
        public_id, restricted_id, body_id = public.id, restricted.id, body.id
    async with database() as db:
        citizen = PersonRepository(db, database, Actor(uuid4()))
        assert await citizen.get(restricted_id) is None
        assert await citizen.get(body_id) is None
        assert [p.id for p in await citizen.list()] == [public_id]
        volunteer = PersonRepository(db, database, Actor(uuid4(), "volunteer"))
        assert await volunteer.get(restricted_id) is not None
        assert await volunteer.get(body_id) is None
        officer = PersonRepository(db, database, Actor(officer_id, "officer"))
        assert await officer.get(body_id) is not None
        await db.rollback()
    async with database() as db:
        audits = list((await db.scalars(select(AuditLog))).all())
        assert len(audits) == 2
        assert all(row.action == "read" and row.meta == {} for row in audits)
        assert {row.object_id for row in audits} == {str(restricted_id), str(body_id)}
        assert any(row.actor_id == officer_id for row in audits)


@pytest.mark.integration
async def test_restricted_writes_audit_and_rollback_atomically(database):
    actor = Actor(uuid4(), "officer")
    async with database() as db, db.begin():
        repo = PersonRepository(db, database, actor)
        person = await repo.create(Person(origin="test", kind="found", access_class="restricted"))
        person_id = person.id
    async with database() as db:
        repo = PersonRepository(db, database, actor)
        await repo.set_status(person_id, "closed")
        await db.rollback()
    async with database() as db:
        assert (await db.get(Person, person_id)).status == "open"
        actions = (await db.scalars(select(AuditLog.action))).all()
        assert sorted(actions) == ["create", "read"]
        denied = PersonRepository(db, database, Actor(uuid4(), "citizen"))
        with pytest.raises(AppError):
            await denied.create(Person(origin="test", kind="missing"))


def test_log_format_only_allowlists_safe_fields():
    import logging

    record = logging.LogRecord("khoj", logging.INFO, "", 1, "request_completed", (), None)
    record.phone = "9876543210"
    record.transcript = "private"
    rendered = JsonFormatter().format(record)
    assert "9876543210" not in rendered and "private" not in rendered
    assert json.loads(rendered)["event"] == "request_completed"


def test_settings_validation_errors_never_print_secrets():
    secret = "private-signing-secret-that-must-never-be-in-tracebacks"
    with pytest.raises(ValidationError) as error:
        Settings(env="production", demo_auth=True, jwt_secret=secret, _env_file=None)
    assert secret not in str(error.value)
