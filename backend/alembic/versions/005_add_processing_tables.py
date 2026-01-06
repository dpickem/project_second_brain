"""Add processing tables for LLM pipeline

Revision ID: 005_add_processing_tables
Revises: 004_rename_content_id
Create Date: 2025-01-03

This migration adds tables for storing LLM processing results:
- processing_runs: Pipeline execution records
- concepts: Extracted concepts
- connections: Content-to-content relationships
- mastery_questions: Generated questions with spaced rep state
- followup_tasks: Generated follow-up tasks
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "005_add_processing_tables"
down_revision: Union[str, None] = "004_rename_content_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create processing_runs table
    op.create_table(
        "processing_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "content_id", sa.Integer(), sa.ForeignKey("content.id"), nullable=False
        ),
        sa.Column("status", sa.String(20), default="pending", index=True),
        sa.Column("started_at", sa.DateTime(), default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        # Analysis results as JSON
        sa.Column("analysis", postgresql.JSONB(), nullable=True),
        sa.Column("summaries", postgresql.JSONB(), nullable=True),
        sa.Column("extraction", postgresql.JSONB(), nullable=True),
        sa.Column("tags", postgresql.JSONB(), nullable=True),
        # Processing metadata
        sa.Column("models_used", postgresql.JSONB(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), default=0),
        sa.Column("estimated_cost_usd", sa.Float(), default=0.0),
        sa.Column("processing_time_seconds", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Output references
        sa.Column("obsidian_note_path", sa.Text(), nullable=True),
        sa.Column("neo4j_node_id", sa.String(64), nullable=True),
    )
    op.create_index("ix_processing_runs_content_id", "processing_runs", ["content_id"])

    # Create concepts table
    op.create_table(
        "concepts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "processing_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processing_runs.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False, index=True),
        sa.Column("definition", sa.Text(), nullable=True),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("importance", sa.String(20), default="supporting"),
        sa.Column("related_concepts", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column("neo4j_node_id", sa.String(64), nullable=True),
    )

    # Create connections table
    op.create_table(
        "connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "processing_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processing_runs.id"),
            nullable=False,
        ),
        sa.Column(
            "source_content_id",
            sa.Integer(),
            sa.ForeignKey("content.id"),
            nullable=False,
        ),
        sa.Column(
            "target_content_id",
            sa.Integer(),
            sa.ForeignKey("content.id"),
            nullable=False,
        ),
        sa.Column("target_title", sa.String(500), nullable=True),  # Cached for display
        sa.Column("relationship_type", sa.String(50), nullable=False),
        sa.Column("strength", sa.Float(), default=0.5),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("verified_by_user", sa.Boolean(), default=False),
    )
    op.create_index("ix_connections_source", "connections", ["source_content_id"])
    op.create_index("ix_connections_target", "connections", ["target_content_id"])

    # Create mastery_questions table
    op.create_table(
        "mastery_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "processing_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processing_runs.id"),
            nullable=False,
        ),
        sa.Column(
            "content_id", sa.Integer(), sa.ForeignKey("content.id"), nullable=False
        ),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(30), default="conceptual"),
        sa.Column("difficulty", sa.String(20), default="intermediate"),
        sa.Column("hints", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("key_points", postgresql.ARRAY(sa.String()), nullable=True),
        # Spaced repetition state
        sa.Column("next_review_at", sa.DateTime(), nullable=True),
        sa.Column("review_count", sa.Integer(), default=0),
        sa.Column("ease_factor", sa.Float(), default=2.5),
        sa.Column("created_at", sa.DateTime(), default=sa.func.now()),
    )
    op.create_index("ix_mastery_questions_content", "mastery_questions", ["content_id"])
    op.create_index(
        "ix_mastery_questions_review", "mastery_questions", ["next_review_at"]
    )

    # Create followup_tasks table
    op.create_table(
        "followup_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "processing_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processing_runs.id"),
            nullable=False,
        ),
        sa.Column(
            "content_id", sa.Integer(), sa.ForeignKey("content.id"), nullable=False
        ),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column("task_type", sa.String(30), default="research"),
        sa.Column("priority", sa.String(10), default="medium"),
        sa.Column("estimated_time", sa.String(20), default="30min"),
        sa.Column("completed", sa.Boolean(), default=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=sa.func.now()),
    )
    op.create_index("ix_followup_tasks_content", "followup_tasks", ["content_id"])
    op.create_index("ix_followup_tasks_completed", "followup_tasks", ["completed"])


def downgrade() -> None:
    op.drop_table("followup_tasks")
    op.drop_table("mastery_questions")
    op.drop_table("connections")
    op.drop_table("concepts")
    op.drop_table("processing_runs")
