"""Add images table

Adds the images table for tracking extracted images from PDF/book content.
Images are stored on disk in the vault but metadata is stored in the database
for efficient querying and proper relational linking to content.

Revision ID: 016
Revises: 015
Create Date: 2026-01-28
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ===========================================
    # Create images table
    # ===========================================
    op.create_table(
        "images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "content_id",
            sa.Integer(),
            sa.ForeignKey("content.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # Content UUID for convenient lookups without joins
        sa.Column(
            "content_uuid",
            sa.String(36),
            nullable=False,
            index=True,
        ),
        # Image file info
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("vault_path", sa.String(1000), nullable=False),
        # Location in source document
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("image_index", sa.Integer(), nullable=False, default=0),
        # Image metadata
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        # Description (from OCR or LLM)
        sa.Column("description", sa.Text(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Create composite index for efficient page-based queries
    op.create_index(
        "ix_images_content_uuid_page",
        "images",
        ["content_uuid", "page_number", "image_index"],
    )


def downgrade() -> None:
    op.drop_index("ix_images_content_uuid_page")
    op.drop_table("images")
