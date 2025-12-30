"""Initial ingestion layer schema

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01

Creates the following tables:
- content: Stores all ingested content (papers, articles, books, etc.)
- annotations: User annotations on content (highlights, notes, etc.)
- tags: Tag definitions
- practice_sessions: Learning sessions
- practice_attempts: Individual practice attempts
- spaced_rep_cards: Spaced repetition cards
- mastery_snapshots: Progress tracking
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create content table
    op.create_table(
        "content",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("source_url", sa.String(2000), nullable=True),
        sa.Column("source_path", sa.String(1000), nullable=True),
        sa.Column("vault_path", sa.String(1000), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING", "PROCESSING", "PROCESSED", "FAILED", name="contentstatus"
            ),
            default="PENDING",
        ),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "metadata_json", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes on content table
    op.create_index("ix_content_content_type", "content", ["content_type"])
    op.create_index("ix_content_status", "content", ["status"])
    op.create_index("ix_content_created_at", "content", ["created_at"])

    # Create annotations table
    op.create_table(
        "annotations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("annotation_type", sa.String(50), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("is_handwritten", sa.Boolean(), default=False),
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["content_id"], ["content.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create index on annotations
    op.create_index("ix_annotations_content_id", "annotations", ["content_id"])

    # Create tags table
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_tags_name", "tags", ["name"])

    # Create practice_sessions table
    op.create_table(
        "practice_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_type", sa.String(50), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("total_cards", sa.Integer(), default=0),
        sa.Column("correct_count", sa.Integer(), default=0),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create spaced_rep_cards table
    op.create_table(
        "spaced_rep_cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=True),
        sa.Column("card_type", sa.String(50), nullable=False),
        sa.Column("front", sa.Text(), nullable=False),
        sa.Column("back", sa.Text(), nullable=False),
        sa.Column("hints", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("ease_factor", sa.Float(), default=2.5),
        sa.Column("interval_days", sa.Integer(), default=1),
        sa.Column("repetitions", sa.Integer(), default=0),
        sa.Column(
            "due_date", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("last_reviewed", sa.DateTime(), nullable=True),
        sa.Column("total_reviews", sa.Integer(), default=0),
        sa.Column("correct_reviews", sa.Integer(), default=0),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["content_id"], ["content.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_spaced_rep_cards_due_date", "spaced_rep_cards", ["due_date"])
    op.create_index(
        "ix_spaced_rep_cards_content_id", "spaced_rep_cards", ["content_id"]
    )

    # Create practice_attempts table
    op.create_table(
        "practice_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("time_taken_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "attempted_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["practice_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["card_id"], ["spaced_rep_cards.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create mastery_snapshots table
    op.create_table(
        "mastery_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "snapshot_date", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("tag_id", sa.Integer(), nullable=True),
        sa.Column("total_cards", sa.Integer(), default=0),
        sa.Column("mastered_cards", sa.Integer(), default=0),
        sa.Column("learning_cards", sa.Integer(), default=0),
        sa.Column("new_cards", sa.Integer(), default=0),
        sa.Column("mastery_score", sa.Float(), default=0.0),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_mastery_snapshots_snapshot_date", "mastery_snapshots", ["snapshot_date"]
    )


def downgrade() -> None:
    op.drop_table("mastery_snapshots")
    op.drop_table("practice_attempts")
    op.drop_table("spaced_rep_cards")
    op.drop_table("practice_sessions")
    op.drop_table("tags")
    op.drop_table("annotations")
    op.drop_table("content")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS contentstatus")
