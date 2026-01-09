"""Add assistant conversations and messages tables

Creates tables for AI assistant chat functionality:
- assistant_conversations: Stores conversation metadata
- assistant_messages: Stores individual messages within conversations

Revision ID: 011
Revises: 010
Create Date: 2026-01-08
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create assistant conversations and messages tables."""
    # Create conversations table
    op.create_table(
        "assistant_conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversation_uuid",
            sa.String(36),
            unique=True,
            index=True,
            nullable=False,
        ),
        sa.Column("title", sa.String(200), server_default="New Conversation"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Create messages table
    op.create_table(
        "assistant_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "message_uuid",
            sa.String(36),
            unique=True,
            index=True,
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum("USER", "ASSISTANT", name="messagerole"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Drop assistant conversations and messages tables."""
    op.drop_table("assistant_messages")
    op.drop_table("assistant_conversations")
    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS messagerole")
