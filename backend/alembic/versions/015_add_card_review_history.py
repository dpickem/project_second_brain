"""Add card review history table

Adds the card_review_history table for tracking individual card reviews
over time. This enables accurate analytics showing review activity per day,
since SpacedRepCard.last_reviewed only stores the most recent review date.

Revision ID: 015
Revises: 014
Create Date: 2026-01-15
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ===========================================
    # Create card_review_history table
    # ===========================================
    op.create_table(
        "card_review_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "card_id",
            sa.Integer(),
            sa.ForeignKey("spaced_rep_cards.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # Review details
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
        sa.Column("time_spent_seconds", sa.Integer(), nullable=True),
        # State tracking
        sa.Column("state_before", sa.String(20), nullable=True),
        sa.Column("state_after", sa.String(20), nullable=True),
        sa.Column("stability_after", sa.Float(), nullable=True),
        sa.Column("scheduled_days", sa.Integer(), nullable=True),
    )

    # Create composite index for efficient date-based queries
    op.create_index(
        "ix_card_review_history_reviewed_at_card_id",
        "card_review_history",
        ["reviewed_at", "card_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_card_review_history_reviewed_at_card_id")
    op.drop_table("card_review_history")
