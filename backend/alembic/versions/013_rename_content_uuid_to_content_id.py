"""Rename content_uuid to content_id in spaced_rep_cards

content_id should ALWAYS mean the UUID throughout the application.
This migration renames the column from content_uuid to content_id
for naming consistency.

Revision ID: 013
Revises: 012
Create Date: 2026-01-14

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename content_uuid to content_id."""
    # Drop old index
    op.drop_index("ix_spaced_rep_cards_content_uuid", table_name="spaced_rep_cards")

    # Rename column
    op.alter_column(
        "spaced_rep_cards",
        "content_uuid",
        new_column_name="content_id",
    )

    # Create new index with correct name
    op.create_index(
        "ix_spaced_rep_cards_content_id",
        "spaced_rep_cards",
        ["content_id"],
    )


def downgrade() -> None:
    """Rename content_id back to content_uuid."""
    # Drop new index
    op.drop_index("ix_spaced_rep_cards_content_id", table_name="spaced_rep_cards")

    # Rename column back
    op.alter_column(
        "spaced_rep_cards",
        "content_id",
        new_column_name="content_uuid",
    )

    # Recreate old index
    op.create_index(
        "ix_spaced_rep_cards_content_uuid",
        "spaced_rep_cards",
        ["content_uuid"],
    )
