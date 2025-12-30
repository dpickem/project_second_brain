"""Add LLM cost tracking tables

Revision ID: 002_cost_tracking
Revises: 001_initial
Create Date: 2025-01-15

Creates the following tables for LLM API cost tracking:
- llm_usage_logs: Individual LLM API call records with cost/token data
- llm_cost_summaries: Pre-aggregated daily/monthly cost summaries

This enables:
- Per-request cost tracking
- Monthly/daily spend reports
- Cost attribution to specific pipelines/content
- Budget alerts and limits
- Model performance vs cost analysis
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "002_cost_tracking"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create llm_usage_logs table
    op.create_table(
        "llm_usage_logs",
        # Primary key
        sa.Column("id", sa.Integer(), nullable=False),
        # Request identification
        sa.Column("request_id", sa.String(64), nullable=False),
        # Model information
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        # Request details
        sa.Column(
            "request_type", sa.String(20), nullable=False
        ),  # vision, text, embedding
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        # Cost tracking (in USD)
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("input_cost_usd", sa.Float(), nullable=True),
        sa.Column("output_cost_usd", sa.Float(), nullable=True),
        # Context for attribution
        sa.Column(
            "pipeline", sa.String(50), nullable=True
        ),  # book_ocr, pdf_processor, etc.
        sa.Column("content_id", sa.Integer(), nullable=True),
        sa.Column(
            "operation", sa.String(100), nullable=True
        ),  # handwriting_detection, etc.
        # Performance metrics
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["content_id"], ["content.id"], ondelete="SET NULL"),
    )

    # Create indexes for common queries
    op.create_index("ix_llm_usage_logs_request_id", "llm_usage_logs", ["request_id"])
    op.create_index("ix_llm_usage_logs_model", "llm_usage_logs", ["model"])
    op.create_index("ix_llm_usage_logs_provider", "llm_usage_logs", ["provider"])
    op.create_index("ix_llm_usage_logs_pipeline", "llm_usage_logs", ["pipeline"])
    op.create_index("ix_llm_usage_logs_content_id", "llm_usage_logs", ["content_id"])
    op.create_index("ix_llm_usage_logs_created_at", "llm_usage_logs", ["created_at"])

    # Composite index for date-based cost queries
    op.create_index(
        "ix_llm_usage_logs_date_model",
        "llm_usage_logs",
        [sa.text("DATE(created_at)"), "model"],
    )

    # Create llm_cost_summaries table for pre-aggregated reporting
    op.create_table(
        "llm_cost_summaries",
        sa.Column("id", sa.Integer(), nullable=False),
        # Time period
        sa.Column("period_type", sa.String(10), nullable=False),  # daily, monthly
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        # Aggregations
        sa.Column("total_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        # Breakdown (JSON)
        sa.Column(
            "cost_by_model", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "cost_by_pipeline", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for summaries
    op.create_index(
        "ix_llm_cost_summaries_period_type", "llm_cost_summaries", ["period_type"]
    )
    op.create_index(
        "ix_llm_cost_summaries_period_start", "llm_cost_summaries", ["period_start"]
    )

    # Unique constraint to prevent duplicate summaries
    op.create_index(
        "ix_llm_cost_summaries_unique_period",
        "llm_cost_summaries",
        ["period_type", "period_start"],
        unique=True,
    )


def downgrade() -> None:
    # Drop llm_cost_summaries
    op.drop_index(
        "ix_llm_cost_summaries_unique_period", table_name="llm_cost_summaries"
    )
    op.drop_index("ix_llm_cost_summaries_period_start", table_name="llm_cost_summaries")
    op.drop_index("ix_llm_cost_summaries_period_type", table_name="llm_cost_summaries")
    op.drop_table("llm_cost_summaries")

    # Drop llm_usage_logs
    op.drop_index("ix_llm_usage_logs_date_model", table_name="llm_usage_logs")
    op.drop_index("ix_llm_usage_logs_created_at", table_name="llm_usage_logs")
    op.drop_index("ix_llm_usage_logs_content_id", table_name="llm_usage_logs")
    op.drop_index("ix_llm_usage_logs_pipeline", table_name="llm_usage_logs")
    op.drop_index("ix_llm_usage_logs_provider", table_name="llm_usage_logs")
    op.drop_index("ix_llm_usage_logs_model", table_name="llm_usage_logs")
    op.drop_index("ix_llm_usage_logs_request_id", table_name="llm_usage_logs")
    op.drop_table("llm_usage_logs")
