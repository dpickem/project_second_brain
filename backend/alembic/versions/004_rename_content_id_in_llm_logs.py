"""Rename content_id to db_content_id and add content_uuid in llm_usage_logs

Revision ID: 004_rename_content_id
Revises: 003_content_uuid
Create Date: 2025-01-03

This migration fixes a design issue where the content_id field was being
overloaded to mean different things (UUID string vs integer FK). Now we have:

- content_uuid: Stores the UUID string as-is from pipelines (for debugging/tracing)
- db_content_id: Stores the resolved integer FK to content.id (for joins)

This separation prevents insidious bugs from type confusion.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "004_rename_content_id"
down_revision = "003_content_uuid"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new content_uuid column for storing UUID strings
    op.add_column(
        "llm_usage_logs",
        sa.Column("content_uuid", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_llm_usage_logs_content_uuid", "llm_usage_logs", ["content_uuid"]
    )

    # Rename content_id to db_content_id
    # First drop the old index
    op.drop_index("ix_llm_usage_logs_content_id", table_name="llm_usage_logs")

    # Rename the column
    op.alter_column(
        "llm_usage_logs",
        "content_id",
        new_column_name="db_content_id",
    )

    # Create new index with new name
    op.create_index(
        "ix_llm_usage_logs_db_content_id", "llm_usage_logs", ["db_content_id"]
    )


def downgrade() -> None:
    # Drop new content_uuid column
    op.drop_index("ix_llm_usage_logs_content_uuid", table_name="llm_usage_logs")
    op.drop_column("llm_usage_logs", "content_uuid")

    # Rename db_content_id back to content_id
    op.drop_index("ix_llm_usage_logs_db_content_id", table_name="llm_usage_logs")

    op.alter_column(
        "llm_usage_logs",
        "db_content_id",
        new_column_name="content_id",
    )

    op.create_index("ix_llm_usage_logs_content_id", "llm_usage_logs", ["content_id"])
