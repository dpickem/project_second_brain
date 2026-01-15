"""No-op migration (work already done in 012)

Originally intended to rename content_uuid to content_id, but migration 012
already handles this correctly by renaming content_id_uuid -> content_id
and creating the index ix_spaced_rep_cards_content_id.

This migration is kept for version history continuity.

Revision ID: 013
Revises: 012
Create Date: 2026-01-14

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op - work already done in migration 012."""
    pass


def downgrade() -> None:
    """No-op - nothing to undo."""
    pass
