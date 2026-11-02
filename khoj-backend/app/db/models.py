"""Canonical PostgreSQL schema. Vector storage is deferred until the feature is enabled."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    REAL,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    phone_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    phone_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    lang: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'hi'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    __table_args__ = (
        CheckConstraint(
            "role in ('citizen','volunteer','officer','admin')", name="users_role_check"
        ),
    )


class IntakeSession(Base):
    __tablename__ = "sessions"
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    lang: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'open'"))
    guest_token_hash: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    __table_args__ = (
        CheckConstraint(
            "kind in ('missing','found','search','status')", name="sessions_kind_check"
        ),
    )


class Turn(Base):
    __tablename__ = "turns"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    idx: Mapped[int] = mapped_column(Integer, nullable=False)
    input_mode: Mapped[str | None] = mapped_column(Text)
    transcript_original: Mapped[str | None] = mapped_column(Text)
    transcript_lang: Mapped[str | None] = mapped_column(Text)
    reply_text: Mapped[str | None] = mapped_column(Text)
    reply_audio_ref: Mapped[str | None] = mapped_column(Text)
    ungrounded: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, server_default=text("'[]'")
    )
    stt_ms: Mapped[int | None] = mapped_column(Integer)
    llm_ms: Mapped[int | None] = mapped_column(Integer)
    tts_ms: Mapped[int | None] = mapped_column(Integer)
    models: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    __table_args__ = (
        CheckConstraint("input_mode in ('voice','text')", name="turns_input_mode_check"),
        UniqueConstraint("session_id", "idx"),
    )


class Person(Base):
    __tablename__ = "persons"
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    origin: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    access_class: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'restricted'")
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'open'"))
    name_original: Mapped[str | None] = mapped_column(Text)
    gender: Mapped[str | None] = mapped_column(Text)
    age_min: Mapped[int | None] = mapped_column(Integer)
    age_max: Mapped[int | None] = mapped_column(Integer)
    height_min: Mapped[int | None] = mapped_column(Integer)
    height_max: Mapped[int | None] = mapped_column(Integer)
    build: Mapped[str | None] = mapped_column(Text)
    complexion: Mapped[str | None] = mapped_column(Text)
    hair: Mapped[str | None] = mapped_column(Text)
    marks_text: Mapped[str | None] = mapped_column(Text)
    language: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    conditions: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    clothing_text: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str | None] = mapped_column(Text)
    district: Mapped[str | None] = mapped_column(Text)
    police_station: Mapped[str | None] = mapped_column(Text)
    place_text: Mapped[str | None] = mapped_column(Text)
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    radius_km: Mapped[float | None] = mapped_column(REAL)
    event_at: Mapped[date | None] = mapped_column(Date)
    attrs: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'")
    )
    search_text: Mapped[str | None] = mapped_column(TSVECTOR)
    content_hash: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    __table_args__ = (
        CheckConstraint(
            "kind in ('missing','found','unidentified_body')", name="persons_kind_check"
        ),
        CheckConstraint(
            "access_class in ('public_summary','restricted','officer_only')",
            name="persons_access_class_check",
        ),
        CheckConstraint(
            "age_min IS NULL OR age_max IS NULL OR age_min <= age_max", name="persons_age_range"
        ),
        CheckConstraint(
            "height_min IS NULL OR height_max IS NULL OR height_min <= height_max",
            name="persons_height_range",
        ),
        Index("persons_blocking", "kind", "state", "gender", "event_at"),
        Index(
            "persons_marks_trgm",
            "marks_text",
            postgresql_using="gin",
            postgresql_ops={"marks_text": "gin_trgm_ops"},
        ),
        Index("persons_search", "search_text", postgresql_using="gin"),
    )


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    case_no: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    person_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id"), nullable=False)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    session_id: Mapped[UUID | None] = mapped_column(ForeignKey("sessions.id"))
    fir_no: Mapped[str | None] = mapped_column(Text)
    relation: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    consent: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("session_id", name="reports_session_unique"),)


class PersonName(Base):
    __tablename__ = "person_names"
    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="CASCADE"), primary_key=True
    )
    name: Mapped[str] = mapped_column(Text, primary_key=True)
    script: Mapped[str | None] = mapped_column(Text)
    phonetic: Mapped[str | None] = mapped_column(Text)


class Photo(Base):
    __tablename__ = "photos"
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    person_id: Mapped[UUID | None] = mapped_column(ForeignKey("persons.id"))
    session_id: Mapped[UUID | None] = mapped_column(ForeignKey("sessions.id"))
    r2_key: Mapped[str] = mapped_column(Text, nullable=False)
    vision_desc: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class Connector(Base):
    __tablename__ = "connectors"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    base_url: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool | None] = mapped_column(Boolean, server_default=text("true"))
    rate_limit_per_min: Mapped[int | None] = mapped_column(Integer)
    terms_reviewed_at: Mapped[date | None] = mapped_column(Date)


class CrawlRun(Base):
    __tablename__ = "crawl_runs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    connector_id: Mapped[str | None] = mapped_column(Text, ForeignKey("connectors.id"))
    slice_key: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rows_seen: Mapped[int | None] = mapped_column(Integer)
    rows_new: Mapped[int | None] = mapped_column(Integer)
    errors: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class RawDocument(Base):
    __tablename__ = "raw_documents"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    connector_id: Mapped[str | None] = mapped_column(Text, ForeignKey("connectors.id"))
    url: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    content_hash: Mapped[str | None] = mapped_column(Text)
    storage_ref: Mapped[str | None] = mapped_column(Text)


class SourceRecord(Base):
    __tablename__ = "source_records"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    connector_id: Mapped[str | None] = mapped_column(Text, ForeignKey("connectors.id"))
    source_id: Mapped[str] = mapped_column(Text, nullable=False)
    raw_doc_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("raw_documents.id"))
    parsed: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    parse_version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(Text)
    source_status: Mapped[str | None] = mapped_column(Text)
    first_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    __table_args__ = (UniqueConstraint("connector_id", "source_id"),)


class PersonSource(Base):
    __tablename__ = "person_sources"
    person_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id"), primary_key=True)
    source_record_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("source_records.id"), primary_key=True
    )


class ScoringVersion(Base):
    __tablename__ = "scoring_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    weights: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    active: Mapped[bool | None] = mapped_column(Boolean, server_default=text("false"))
    __table_args__ = (
        Index(
            "scoring_versions_one_active", "active", unique=True, postgresql_where=text("active")
        ),
    )


class Matche(Base):
    __tablename__ = "matches"
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    missing_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id"), nullable=False)
    found_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id"), nullable=False)
    scoring_version: Mapped[int | None] = mapped_column(Integer, ForeignKey("scoring_versions.id"))
    score: Mapped[float] = mapped_column(REAL, nullable=False)
    band: Mapped[str] = mapped_column(Text, nullable=False)
    signals: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'tiered'"))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    __table_args__ = (
        CheckConstraint("band in ('strong','possible','weak')", name="matches_band_check"),
        CheckConstraint(
            "status in ('tiered','pending_review','approved','rejected','notified','expired')",
            name="matches_status_check",
        ),
        UniqueConstraint("missing_id", "found_id"),
    )


class LLMCache(Base):
    __tablename__ = "llm_cache"
    pair_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    role: Mapped[str] = mapped_column(Text, primary_key=True)
    model: Mapped[str | None] = mapped_column(Text)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    match_id: Mapped[UUID | None] = mapped_column(ForeignKey("matches.id"))
    reviewer_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    __table_args__ = (
        CheckConstraint(
            "decision in ('approve','reject','needs_info')", name="reviews_decision_check"
        ),
    )


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    match_id: Mapped[UUID | None] = mapped_column(ForeignKey("matches.id"))
    audience: Mapped[str | None] = mapped_column(Text)
    template_id: Mapped[str | None] = mapped_column(Text)
    lang: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(Text, server_default=text("'queued'"))
    idempotency_key: Mapped[str | None] = mapped_column(Text, unique=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Watche(Base):
    __tablename__ = "watches"
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    report_id: Mapped[UUID | None] = mapped_column(ForeignKey("reports.id"))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    records_checked: Mapped[int | None] = mapped_column(BigInteger, server_default=text("0"))
    active: Mapped[bool | None] = mapped_column(Boolean, server_default=text("true"))


class CaseEvent(Base):
    __tablename__ = "case_events"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    report_id: Mapped[UUID | None] = mapped_column(ForeignKey("reports.id"))
    at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    kind: Mapped[str | None] = mapped_column(Text)
    text_key: Mapped[str | None] = mapped_column(Text)
    params: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    actor_id: Mapped[UUID | None] = mapped_column()
    actor_role: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str | None] = mapped_column(Text)
    object_type: Mapped[str | None] = mapped_column(Text)
    object_id: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class Consent(Base):
    __tablename__ = "consents"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[UUID | None] = mapped_column()
    purpose: Mapped[str | None] = mapped_column(Text)
    text_version: Mapped[str | None] = mapped_column(Text)
    granted: Mapped[bool | None] = mapped_column(Boolean)
    at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class GazetteerPlace(Base):
    __tablename__ = "gazetteer_places"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str | None] = mapped_column(Text)
    name_hi: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str | None] = mapped_column(Text)
    district: Mapped[str | None] = mapped_column(Text)
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)


class Outbox(Base):
    __tablename__ = "outbox"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    channel: Mapped[str | None] = mapped_column(Text)
    to_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    template_id: Mapped[str | None] = mapped_column(Text)
    params: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    status: Mapped[str | None] = mapped_column(Text, server_default=text("'queued'"))
    demo: Mapped[bool | None] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("auth_sessions.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (Index("refresh_tokens_session", "session_id"),)


class IntakeRequest(Base):
    __tablename__ = "intake_requests"
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    body_hash: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class IntakeClip(Base):
    __tablename__ = "intake_clips"
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    turn_id: Mapped[str] = mapped_column(Text, primary_key=True)
    clip_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)


class IntakeMatchJob(Base):
    __tablename__ = "intake_match_jobs"
    person_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id"), primary_key=True)
    report_id: Mapped[UUID] = mapped_column(ForeignKey("reports.id"), nullable=False)
    enqueued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SpeechSegment(Base):
    __tablename__ = "speech_segments"
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    lang: Mapped[str] = mapped_column(Text, nullable=False)
    voice: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    speed: Mapped[float] = mapped_column(Float, nullable=False)
