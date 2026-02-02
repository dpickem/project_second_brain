"""Add lineage tracking for cards and exercises

Adds concept-level tracking to enable deduplication:
- source_concept: Tracks which concept generated each card/exercise
- exercise_content: Junction table for Exercise <-> Content many-to-many

This enables:
- Checking if cards/exercises already exist for a concept
- Proper reverse lookups from Content to Exercises
- Deduplication during content processing

Revision ID: 017
Revises: 016
Create Date: 2026-02-01
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add source_concept to spaced_rep_cards
    # Stores the concept name that generated this card for deduplication
    op.add_column(
        "spaced_rep_cards",
        sa.Column("source_concept", sa.String(255), nullable=True),
    )
    
    # Create composite index for efficient dedup queries:
    # "Does content X already have a card for concept Y?"
    op.create_index(
        "ix_spaced_rep_cards_content_concept",
        "spaced_rep_cards",
        ["source_content_pk", "source_concept"],
        unique=False,
    )
    
    # 2. Add source_concept to exercises
    # Stores the concept name that generated this exercise
    op.add_column(
        "exercises",
        sa.Column("source_concept", sa.String(255), nullable=True),
    )
    
    # 3. Create exercise_content junction table for proper many-to-many
    # This replaces the source_content_ids array for better queryability
    op.create_table(
        "exercise_content",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "exercise_id",
            sa.Integer,
            sa.ForeignKey("exercises.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "content_id",
            sa.Integer,
            sa.ForeignKey("content.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Store the content UUID as well for convenience
        sa.Column("content_uuid", sa.String(36), nullable=False, index=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    
    # Unique constraint: an exercise can only be linked to a content once
    op.create_index(
        "ix_exercise_content_unique",
        "exercise_content",
        ["exercise_id", "content_id"],
        unique=True,
    )
    
    # Index for efficient reverse lookups: "What exercises came from this content?"
    op.create_index(
        "ix_exercise_content_content_id",
        "exercise_content",
        ["content_id"],
    )
    
    # Index for dedup queries: "Does content X already have an exercise for concept Y?"
    op.create_index(
        "ix_exercises_source_concept",
        "exercises",
        ["source_concept"],
    )


def downgrade() -> None:
    # Drop junction table
    op.drop_index("ix_exercise_content_content_id", table_name="exercise_content")
    op.drop_index("ix_exercise_content_unique", table_name="exercise_content")
    op.drop_table("exercise_content")
    
    # Drop exercise source_concept
    op.drop_index("ix_exercises_source_concept", table_name="exercises")
    op.drop_column("exercises", "source_concept")
    
    # Drop card source_concept
    op.drop_index("ix_spaced_rep_cards_content_concept", table_name="spaced_rep_cards")
    op.drop_column("spaced_rep_cards", "source_concept")
