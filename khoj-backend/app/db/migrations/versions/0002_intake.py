"""Durable intake ownership, idempotency, clips, speech and LangGraph 3.2.0 schema.

Checkpoint SQL is a frozen snapshot, not imported from a future dependency version.
"""

from pathlib import Path

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for statement in Path(__file__).with_suffix(".sql").read_text().split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    for name in (
        "speech_segments",
        "intake_match_jobs",
        "intake_clips",
        "intake_requests",
        "checkpoint_writes",
        "checkpoint_blobs",
        "checkpoints",
        "checkpoint_migrations",
    ):
        op.drop_table(name)
    op.drop_constraint("reports_session_unique", "reports", type_="unique")
    op.drop_column("photos", "session_id")
    op.drop_column("sessions", "guest_token_hash")
