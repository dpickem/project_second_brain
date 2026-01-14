"""Change spaced_rep_cards.content_id from integer FK to UUID string

content_id should ALWAYS mean the UUID throughout the application.
The database integer ID is an internal implementation detail that
should only be used in SQL joins/queries, never exposed to the app.

This migration:
1. Converts content_id from int FK to UUID string
2. Preserves the data by looking up UUIDs via the old FK relationship

Revision ID: 012
Revises: 011
Create Date: 2026-01-14

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Convert content_id from integer FK to UUID string.

    Steps:
    1. Add temp column for UUID
    2. Populate UUID from content table via the old FK
    3. Drop old content_id (int) column and FK constraint
    4. Add new content_id (string) column
    5. Copy data from temp to new content_id
    6. Drop temp column
    7. Add index
    """
    # Add temp column for UUID
    op.add_column(
        "spaced_rep_cards",
        sa.Column("content_id_uuid", sa.String(36), nullable=True),
    )

    # Populate UUID from content table via the old integer FK
    op.execute(
        """
        UPDATE spaced_rep_cards
        SET content_id_uuid = content.content_uuid
        FROM content
        WHERE spaced_rep_cards.content_id = content.id
        """
    )

    # Drop the foreign key constraint
    op.drop_constraint(
        "spaced_rep_cards_content_id_fkey", "spaced_rep_cards", type_="foreignkey"
    )

    # Drop the old integer content_id column
    op.drop_column("spaced_rep_cards", "content_id")

    # Rename temp column to content_id
    op.alter_column(
        "spaced_rep_cards",
        "content_id_uuid",
        new_column_name="content_id",
    )

    # Add index on content_id for efficient lookups
    op.create_index(
        "ix_spaced_rep_cards_content_id",
        "spaced_rep_cards",
        ["content_id"],
    )


def downgrade() -> None:
    """
    Revert content_id from UUID string back to integer FK.

    Note: This may lose data if content was deleted since the upgrade.
    """
    # Drop the index
    op.drop_index("ix_spaced_rep_cards_content_id", table_name="spaced_rep_cards")

    # Rename content_id to temp
    op.alter_column(
        "spaced_rep_cards",
        "content_id",
        new_column_name="content_id_uuid",
    )

    # Add back the integer content_id column
    op.add_column(
        "spaced_rep_cards",
        sa.Column("content_id", sa.Integer(), nullable=True),
    )

    # Populate integer from content table via UUID
    op.execute(
        """
        UPDATE spaced_rep_cards
        SET content_id = content.id
        FROM content
        WHERE spaced_rep_cards.content_id_uuid = content.content_uuid
        """
    )

    # Re-add the foreign key constraint
    op.create_foreign_key(
        "spaced_rep_cards_content_id_fkey",
        "spaced_rep_cards",
        "content",
        ["content_id"],
        ["id"],
    )

    # Drop the temp column
    op.drop_column("spaced_rep_cards", "content_id_uuid")
