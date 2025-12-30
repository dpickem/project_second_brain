"""Add content_uuid column to content table

Revision ID: 003_content_uuid
Revises: 002_cost_tracking
Create Date: 2025-01-15

Adds a dedicated content_uuid column to the content table for efficient lookups.
Previously, the UUID was stored in metadata_json["id"], requiring JSON parsing.

This migration:
1. Adds content_uuid column (nullable initially for existing rows)
2. Migrates existing UUIDs from metadata_json["id"] to the new column
3. Sets NOT NULL constraint after migration
4. Creates unique index for fast lookups

Benefits:
- Direct column lookup vs JSON parsing (much faster)
- Proper unique constraint enforcement at DB level
- Cleaner API: content.content_uuid vs content.metadata_json["id"]
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "003_content_uuid"
down_revision = "002_cost_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Add column as nullable (to allow migration of existing data)
    op.add_column("content", sa.Column("content_uuid", sa.String(36), nullable=True))

    # Step 2: Migrate existing UUIDs from metadata_json["id"] to new column
    # This handles existing rows that stored UUID in the JSON field
    op.execute(
        """
        UPDATE content 
        SET content_uuid = metadata_json->>'id'
        WHERE metadata_json->>'id' IS NOT NULL
          AND content_uuid IS NULL
    """
    )

    # Step 3: For any rows without UUID in metadata, generate new UUIDs
    # This ensures all rows have a content_uuid
    op.execute(
        """
        UPDATE content 
        SET content_uuid = gen_random_uuid()::text
        WHERE content_uuid IS NULL
    """
    )

    # Step 4: Now set NOT NULL constraint since all rows have values
    op.alter_column("content", "content_uuid", nullable=False)

    # Step 5: Create unique index for fast lookups
    op.create_index("ix_content_content_uuid", "content", ["content_uuid"], unique=True)


def downgrade() -> None:
    # Remove index first
    op.drop_index("ix_content_content_uuid", table_name="content")

    # Remove column
    op.drop_column("content", "content_uuid")
