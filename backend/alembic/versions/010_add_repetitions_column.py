"""Add repetitions column to spaced_rep_cards

Migration 007 dropped the repetitions column during SM-2 to FSRS migration,
but the column is still needed for FSRS tracking of consecutive successful reviews.

Revision ID: 010
Revises: 009
Create Date: 2026-01-08
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add repetitions column back to spaced_rep_cards."""
    op.add_column(
        "spaced_rep_cards",
        sa.Column("repetitions", sa.Integer(), nullable=True, server_default="0"),
    )


def downgrade() -> None:
    """Remove repetitions column from spaced_rep_cards."""
    op.drop_column("spaced_rep_cards", "repetitions")
