"""Add source_content_pk FK to spaced_rep_cards for ORM relationship

Cards now have both:
- content_id (str): UUID string - the app-facing identifier
- source_content_pk (int FK): Database FK for ORM relationship

This enables proper SQLAlchemy relationship while keeping
content_id as the primary application identifier.

Revision ID: 014
Revises: 013
Create Date: 2026-01-14

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add source_content_pk FK column and populate from content_id."""
    # Add the FK column
    op.add_column(
        "spaced_rep_cards",
        sa.Column("source_content_pk", sa.Integer(), nullable=True),
    )

    # Populate from content table via content_id (UUID)
    op.execute(
        """
        UPDATE spaced_rep_cards
        SET source_content_pk = content.id
        FROM content
        WHERE spaced_rep_cards.content_id = content.content_uuid
        """
    )

    # Add FK constraint
    op.create_foreign_key(
        "spaced_rep_cards_source_content_pk_fkey",
        "spaced_rep_cards",
        "content",
        ["source_content_pk"],
        ["id"],
    )

    # Add index for efficient joins
    op.create_index(
        "ix_spaced_rep_cards_source_content_pk",
        "spaced_rep_cards",
        ["source_content_pk"],
    )


def downgrade() -> None:
    """Remove source_content_pk column."""
    op.drop_index(
        "ix_spaced_rep_cards_source_content_pk", table_name="spaced_rep_cards"
    )
    op.drop_constraint(
        "spaced_rep_cards_source_content_pk_fkey",
        "spaced_rep_cards",
        type_="foreignkey",
    )
    op.drop_column("spaced_rep_cards", "source_content_pk")
