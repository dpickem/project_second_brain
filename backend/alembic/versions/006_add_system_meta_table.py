"""Add system_meta table for vault sync state

Revision ID: 006_add_system_meta
Revises: 005_add_processing_tables
Create Date: 2026-01-05

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "006_add_system_meta"
down_revision = "005_add_processing_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create system_meta table for key-value storage of system state."""
    op.create_table(
        "system_meta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_system_meta_key"), "system_meta", ["key"], unique=True)


def downgrade() -> None:
    """Drop system_meta table."""
    op.drop_index(op.f("ix_system_meta_key"), table_name="system_meta")
    op.drop_table("system_meta")
