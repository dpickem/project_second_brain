"""Convert all timestamp columns to TIMESTAMP WITH TIME ZONE

Revision ID: 008
Revises: 007
Create Date: 2026-01-07

This migration converts all TIMESTAMP columns to TIMESTAMP WITH TIME ZONE
for consistent timezone-aware datetime handling across the application.

PostgreSQL will interpret existing naive timestamps as UTC during conversion.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


# All timestamp columns to convert, grouped by table
# Format: {table: [(column, has_index), ...]}
# Only includes tables that exist after migration 007
TIMESTAMP_COLUMNS = {
    # models.py tables
    "content": [
        ("created_at", False),
        ("processed_at", False),
        ("updated_at", False),
    ],
    "annotations": [("created_at", False)],
    "tags": [("created_at", False)],
    "llm_usage_logs": [("created_at", True)],  # has index ix_llm_usage_logs_created_at
    "llm_cost_summaries": [
        ("period_start", True),  # has index
        ("period_end", False),
        ("created_at", False),
        ("updated_at", False),
    ],
    "system_meta": [("created_at", False), ("updated_at", False)],
    # models_learning.py tables
    "practice_sessions": [("started_at", False), ("ended_at", False)],
    "practice_attempts": [("attempted_at", False)],
    "spaced_rep_cards": [
        ("due_date", False),
        ("last_reviewed", False),
        ("created_at", False),
    ],
    "mastery_snapshots": [("snapshot_date", False), ("last_practiced", False)],
    "exercises": [("created_at", False), ("updated_at", False)],  # created by 007
    "exercise_attempts": [("attempted_at", False)],  # created by 007
    # models_processing.py tables
    "processing_runs": [("started_at", False), ("completed_at", False)],
    "mastery_questions": [
        ("next_review_at", True),
        ("created_at", False),
    ],  # next_review_at has index
    "followup_tasks": [
        ("completed_at", False),
        ("created_at", False),
    ],  # NOT followup_records!
}

# Functional indexes that depend on timestamp columns
# These must be dropped before altering the column type
FUNCTIONAL_INDEXES = [
    # Index: (name, table, recreate_sql)
    # After migration, created_at is TIMESTAMPTZ. We extract UTC date for consistent indexing.
    (
        "ix_llm_usage_logs_date_model",
        "llm_usage_logs",
        "CREATE INDEX ix_llm_usage_logs_date_model ON llm_usage_logs (CAST(created_at AT TIME ZONE 'UTC' AS date), model)",
    ),
]


def upgrade() -> None:
    """Convert all timestamp columns to TIMESTAMP WITH TIME ZONE.

    We set the session timezone to UTC first, then PostgreSQL will
    interpret existing naive timestamps as UTC during the type change.
    """
    # Set session timezone to UTC so naive timestamps are interpreted as UTC
    op.execute("SET timezone = 'UTC'")

    # Drop functional indexes that depend on timestamp columns
    for index_name, table_name, _ in FUNCTIONAL_INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {index_name}")

    for table, columns in TIMESTAMP_COLUMNS.items():
        for column, has_index in columns:
            # Default index name in SQLAlchemy is ix_<table>_<column>
            index_name = f"ix_{table}_{column}"

            if has_index:
                # Drop the simple column index first (if it exists)
                op.execute(f"DROP INDEX IF EXISTS {index_name}")

            # Simple ALTER COLUMN - PostgreSQL interprets naive timestamps
            # using session timezone (UTC) during conversion
            op.execute(
                f"ALTER TABLE {table} "
                f"ALTER COLUMN {column} TYPE TIMESTAMP WITH TIME ZONE"
            )

            if has_index:
                # Recreate the simple column index
                op.create_index(index_name, table, [column])

    # Recreate functional indexes with timezone-aware expression
    for index_name, table_name, create_stmt in FUNCTIONAL_INDEXES:
        op.execute(create_stmt)


def downgrade() -> None:
    """Convert timestamp columns back to TIMESTAMP WITHOUT TIME ZONE.

    This strips timezone info, keeping the UTC value.
    """
    op.execute("SET timezone = 'UTC'")

    # Drop functional indexes
    for index_name, table_name, _ in FUNCTIONAL_INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {index_name}")

    for table, columns in TIMESTAMP_COLUMNS.items():
        for column, has_index in columns:
            index_name = f"ix_{table}_{column}"

            if has_index:
                op.execute(f"DROP INDEX IF EXISTS {index_name}")

            # Convert back to naive timestamp
            op.execute(
                f"ALTER TABLE {table} "
                f"ALTER COLUMN {column} TYPE TIMESTAMP WITHOUT TIME ZONE"
            )

            if has_index:
                op.create_index(index_name, table, [column])

    # Recreate functional indexes for naive timestamps
    op.execute(
        "CREATE INDEX ix_llm_usage_logs_date_model ON llm_usage_logs (date(created_at), model)"
    )
