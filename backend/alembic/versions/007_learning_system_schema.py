"""Learning System Schema

Extends the database schema for the full Learning System implementation:
- Upgrades SpacedRepCard from SM-2 to FSRS algorithm
- Creates Exercise table for exercise generation
- Creates ExerciseAttempt table for tracking exercise responses
- Enhances MasterySnapshot with topic tracking
- Enhances PracticeSession with analytics fields

Revision ID: 007
Revises: 006
Create Date: 2026-01-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "007"
down_revision = "006_add_system_meta"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ===========================================
    # Extend SpacedRepCard with FSRS fields
    # ===========================================

    # Add FSRS-specific columns to spaced_rep_cards
    op.add_column(
        "spaced_rep_cards",
        sa.Column("stability", sa.Float(), nullable=True, server_default="0.0"),
    )
    op.add_column(
        "spaced_rep_cards",
        sa.Column("difficulty", sa.Float(), nullable=True, server_default="0.3"),
    )
    op.add_column(
        "spaced_rep_cards",
        sa.Column(
            "state",
            sa.String(20),
            nullable=True,
            server_default="new",
        ),
    )
    op.add_column(
        "spaced_rep_cards",
        sa.Column("lapses", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column(
        "spaced_rep_cards",
        sa.Column("scheduled_days", sa.Integer(), nullable=True, server_default="0"),
    )

    # Code-specific card fields
    op.add_column(
        "spaced_rep_cards",
        sa.Column("language", sa.String(50), nullable=True),
    )
    op.add_column(
        "spaced_rep_cards",
        sa.Column("starter_code", sa.Text(), nullable=True),
    )
    op.add_column(
        "spaced_rep_cards",
        sa.Column("solution_code", sa.Text(), nullable=True),
    )
    op.add_column(
        "spaced_rep_cards",
        sa.Column(
            "test_cases",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # Tags and concept linking
    op.add_column(
        "spaced_rep_cards",
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String()),
            nullable=True,
        ),
    )
    op.add_column(
        "spaced_rep_cards",
        sa.Column("concept_id", sa.String(64), nullable=True),
    )

    # Add indexes for efficient queries
    op.create_index(
        "ix_spaced_rep_cards_due_state",
        "spaced_rep_cards",
        ["due_date", "state"],
    )
    op.create_index(
        "ix_spaced_rep_cards_concept",
        "spaced_rep_cards",
        ["concept_id"],
    )

    # Drop legacy SM-2 columns (replaced by FSRS)
    op.drop_column("spaced_rep_cards", "ease_factor")
    op.drop_column("spaced_rep_cards", "interval_days")
    op.drop_column("spaced_rep_cards", "repetitions")

    # ===========================================
    # Create Exercise table
    # ===========================================
    op.create_table(
        "exercises",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "exercise_uuid",
            sa.String(36),
            unique=True,
            index=True,
            nullable=False,
        ),
        sa.Column(
            "exercise_type",
            sa.String(50),
            nullable=False,
            index=True,
        ),
        sa.Column("topic", sa.String(200), nullable=False, index=True),
        sa.Column(
            "difficulty", sa.String(20), nullable=False, server_default="intermediate"
        ),
        # Exercise content
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("hints", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("expected_key_points", postgresql.ARRAY(sa.String()), nullable=True),
        # For worked examples
        sa.Column("worked_example", sa.Text(), nullable=True),
        sa.Column("follow_up_problem", sa.Text(), nullable=True),
        # For code exercises
        sa.Column("language", sa.String(50), nullable=True),
        sa.Column("starter_code", sa.Text(), nullable=True),
        sa.Column("solution_code", sa.Text(), nullable=True),
        sa.Column(
            "test_cases",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        # For debugging exercises
        sa.Column("buggy_code", sa.Text(), nullable=True),
        # Source and metadata
        sa.Column(
            "source_content_ids",
            postgresql.ARRAY(sa.String()),
            nullable=True,
        ),
        sa.Column(
            "estimated_time_minutes", sa.Integer(), nullable=True, server_default="10"
        ),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    # Composite index for efficient filtering
    op.create_index(
        "ix_exercises_type_difficulty",
        "exercises",
        ["exercise_type", "difficulty"],
    )

    # ===========================================
    # Create ExerciseAttempt table
    # ===========================================
    op.create_table(
        "exercise_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "attempt_uuid",
            sa.String(36),
            unique=True,
            index=True,
            nullable=False,
        ),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("practice_sessions.id"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "exercise_id",
            sa.Integer(),
            sa.ForeignKey("exercises.id"),
            nullable=False,
            index=True,
        ),
        # Response content
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("response_code", sa.Text(), nullable=True),
        # Evaluation results
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        # Detailed evaluation
        sa.Column("covered_points", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("missing_points", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("misconceptions", postgresql.ARRAY(sa.String()), nullable=True),
        # Code evaluation results
        sa.Column("tests_passed", sa.Integer(), nullable=True),
        sa.Column("tests_total", sa.Integer(), nullable=True),
        sa.Column(
            "test_results",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("execution_error", sa.Text(), nullable=True),
        # Confidence tracking
        sa.Column("confidence_before", sa.Integer(), nullable=True),
        sa.Column("confidence_after", sa.Integer(), nullable=True),
        # Timing
        sa.Column("time_spent_seconds", sa.Integer(), nullable=True),
        # Timestamps
        sa.Column(
            "attempted_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    # ===========================================
    # Extend MasterySnapshot with topic tracking
    # ===========================================
    op.add_column(
        "mastery_snapshots",
        sa.Column("topic_path", sa.String(200), nullable=True, index=True),
    )
    op.add_column(
        "mastery_snapshots",
        sa.Column("practice_count", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column(
        "mastery_snapshots",
        sa.Column("success_rate", sa.Float(), nullable=True),
    )
    op.add_column(
        "mastery_snapshots",
        sa.Column("trend", sa.String(20), nullable=True),
    )
    op.add_column(
        "mastery_snapshots",
        sa.Column("last_practiced", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "mastery_snapshots",
        sa.Column("retention_estimate", sa.Float(), nullable=True),
    )
    op.add_column(
        "mastery_snapshots",
        sa.Column("days_since_review", sa.Integer(), nullable=True),
    )

    # Composite index for querying by date and topic
    op.create_index(
        "ix_mastery_date_topic",
        "mastery_snapshots",
        ["snapshot_date", "topic_path"],
    )

    # ===========================================
    # Extend PracticeSession with analytics
    # ===========================================
    op.add_column(
        "practice_sessions",
        sa.Column("topics_covered", postgresql.ARRAY(sa.String()), nullable=True),
    )
    op.add_column(
        "practice_sessions",
        sa.Column("exercise_count", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column(
        "practice_sessions",
        sa.Column("average_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "practice_sessions",
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    # ===========================================
    # Drop PracticeSession extensions (columns only - table existed before)
    # ===========================================
    op.drop_column("practice_sessions", "duration_minutes")
    op.drop_column("practice_sessions", "average_score")
    op.drop_column("practice_sessions", "exercise_count")
    op.drop_column("practice_sessions", "topics_covered")

    # ===========================================
    # Drop MasterySnapshot extensions (columns only - table existed before)
    # ===========================================
    op.drop_index("ix_mastery_date_topic", table_name="mastery_snapshots")
    op.drop_column("mastery_snapshots", "days_since_review")
    op.drop_column("mastery_snapshots", "retention_estimate")
    op.drop_column("mastery_snapshots", "last_practiced")
    op.drop_column("mastery_snapshots", "trend")
    op.drop_column("mastery_snapshots", "success_rate")
    op.drop_column("mastery_snapshots", "practice_count")
    op.drop_column("mastery_snapshots", "topic_path")

    # ===========================================
    # Drop ExerciseAttempt table (entire table - created in this migration)
    # ===========================================
    op.drop_table("exercise_attempts")

    # ===========================================
    # Drop Exercise table (entire table - created in this migration)
    # ===========================================
    op.drop_index("ix_exercises_type_difficulty", table_name="exercises")
    op.drop_table("exercises")

    # ===========================================
    # Drop SpacedRepCard extensions (columns only - table existed before)
    # ===========================================
    op.drop_index("ix_spaced_rep_cards_concept", table_name="spaced_rep_cards")
    op.drop_index("ix_spaced_rep_cards_due_state", table_name="spaced_rep_cards")
    op.drop_column("spaced_rep_cards", "concept_id")
    op.drop_column("spaced_rep_cards", "tags")
    op.drop_column("spaced_rep_cards", "test_cases")
    op.drop_column("spaced_rep_cards", "solution_code")
    op.drop_column("spaced_rep_cards", "starter_code")
    op.drop_column("spaced_rep_cards", "language")
    op.drop_column("spaced_rep_cards", "scheduled_days")
    op.drop_column("spaced_rep_cards", "lapses")
    op.drop_column("spaced_rep_cards", "state")
    op.drop_column("spaced_rep_cards", "difficulty")
    op.drop_column("spaced_rep_cards", "stability")

    # Restore legacy SM-2 columns
    op.add_column(
        "spaced_rep_cards",
        sa.Column("ease_factor", sa.Float(), nullable=False, server_default="2.5"),
    )
    op.add_column(
        "spaced_rep_cards",
        sa.Column("interval_days", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "spaced_rep_cards",
        sa.Column("repetitions", sa.Integer(), nullable=False, server_default="0"),
    )
