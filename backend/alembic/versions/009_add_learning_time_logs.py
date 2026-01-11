"""Add learning time logs table

Adds the learning_time_logs table for tracking time spent
on learning activities (reviews, practice sessions, reading).

Revision ID: 009
Revises: 008
Create Date: 2026-01-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ===========================================
    # Create learning_time_logs table
    # ===========================================
    op.create_table(
        "learning_time_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        # What was being learned
        sa.Column("topic", sa.String(200), nullable=True, index=True),
        sa.Column(
            "content_id", sa.Integer(), sa.ForeignKey("content.id"), nullable=True
        ),
        # Activity type: review, practice, reading, exercise
        sa.Column("activity_type", sa.String(50), nullable=False, index=True),
        # Time tracking
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        # Metadata
        sa.Column("items_completed", sa.Integer(), nullable=False, default=0),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("practice_sessions.id"),
            nullable=True,
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Create indexes for efficient queries
    op.create_index(
        "ix_learning_time_logs_started_at",
        "learning_time_logs",
        ["started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_learning_time_logs_started_at")
    op.drop_table("learning_time_logs")
