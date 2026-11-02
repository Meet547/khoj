"""Initial architecture schema, auth session rotation, audit support.

The immutable SQL snapshot does not import application ORM metadata.
"""

from pathlib import Path

import sqlalchemy as sa
from alembic import op

from app.config import get_settings

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    for statement in Path(__file__).with_name("0001_schema.sql").read_text().split(";"):
        if statement.strip():
            op.execute(sa.text(statement))
    if get_settings().enable_pgvector:
        available = (
            op.get_bind()
            .execute(
                sa.text(
                    "SELECT EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector')"
                )
            )
            .scalar()
        )
        if available:
            op.execute("CREATE EXTENSION IF NOT EXISTS vector")
            op.execute("ALTER TABLE photos ADD COLUMN face_vec vector(512)")


def downgrade() -> None:
    op.execute("DROP VIEW citizen_persons")
    # Explicit order keeps rollback predictable and avoids CASCADE into unrelated schemas.
    for table in (
        "refresh_tokens",
        "auth_sessions",
        "outbox",
        "gazetteer_places",
        "consents",
        "audit_log",
        "case_events",
        "watches",
        "alerts",
        "reviews",
        "llm_cache",
        "matches",
        "scoring_versions",
        "person_sources",
        "source_records",
        "raw_documents",
        "crawl_runs",
        "connectors",
        "photos",
        "person_names",
        "reports",
        "persons",
        "turns",
        "sessions",
        "users",
    ):
        op.drop_table(table)
    op.execute("DROP SEQUENCE case_number_seq")
    # Extensions may be shared by other applications and deliberately remain installed.
