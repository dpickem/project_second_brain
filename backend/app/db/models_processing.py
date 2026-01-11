"""
SQLAlchemy Database Models for LLM Processing

These models store processing results, enabling:
- Audit trails for all processing runs
- Reprocessing with updated prompts/models
- User feedback on generated content
- Analytics on processing quality and cost

ARCHITECTURE NOTE:
    This file contains SQLALCHEMY models for database persistence.
    There is a corresponding Pydantic file: app/models/processing.py

    Why two files?
    - Pydantic models: JSON parsing, API validation, pipeline data flow
    - SQLAlchemy models: Database schema, ORM, persistence, foreign keys

    Data flows: LLM Output → Pydantic → Pipeline → SQLAlchemy → Database

    Fields like `processing_run_id` and `content_id` (foreign keys) exist only
    here since they're database concerns for relational integrity.

    The two model sets are kept in sync - if you add a field to one,
    consider whether it belongs in the other.

Tables:
- processing_runs: Record of pipeline executions
- concepts: Extracted concepts
- connections: Discovered content connections
- mastery_questions: Generated questions with spaced repetition state
- followup_tasks: Generated follow-up tasks
"""

from datetime import datetime, timezone
from typing import List, Optional
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.enums import ConceptImportance


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class ProcessingRun(Base):
    """
    Record of a processing pipeline execution.

    Each time content is processed through the LLM pipeline, a record is created
    here. This enables:
    - Tracking processing history
    - Comparing results across different model versions
    - Reprocessing when prompts are updated
    - Cost and performance analytics

    Attributes:
        id: Primary key UUID
        content_id: Foreign key to content being processed
        status: Current status (pending, processing, completed, failed)
        started_at: When processing began
        completed_at: When processing finished (null if in progress/failed)
        analysis: ContentAnalysis result as JSON
        summaries: Dict of summaries by level
        extraction: ExtractionResult as JSON
        tags: TagAssignment as JSON
        models_used: Mapping of stage -> model used
        total_tokens: Total tokens consumed
        estimated_cost_usd: Estimated cost in USD
        processing_time_seconds: Total wall-clock time
        error_message: Error details if failed
        obsidian_note_path: Path to generated note
        neo4j_node_id: ID of created graph node
    """

    __tablename__ = "processing_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    content_id: Mapped[int] = mapped_column(
        ForeignKey("content.id"), nullable=False, index=True
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20), default="pending", index=True
    )  # pending, processing, completed, failed
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Analysis results (stored as JSON for flexibility)
    analysis: Mapped[Optional[dict]] = mapped_column(JSONB)
    summaries: Mapped[Optional[dict]] = mapped_column(JSONB)  # {level: summary}
    extraction: Mapped[Optional[dict]] = mapped_column(JSONB)
    tags: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Processing metadata
    models_used: Mapped[Optional[dict]] = mapped_column(JSONB)  # {stage: model}
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    processing_time_seconds: Mapped[Optional[float]] = mapped_column(Float)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Output references
    obsidian_note_path: Mapped[Optional[str]] = mapped_column(Text)
    neo4j_node_id: Mapped[Optional[str]] = mapped_column(String(64))

    # Relationships
    content: Mapped["Content"] = relationship(back_populates="processing_runs")
    concepts: Mapped[List["ConceptRecord"]] = relationship(
        back_populates="processing_run", cascade="all, delete-orphan"
    )
    connections: Mapped[List["ConnectionRecord"]] = relationship(
        back_populates="processing_run", cascade="all, delete-orphan"
    )
    questions: Mapped[List["QuestionRecord"]] = relationship(
        back_populates="processing_run", cascade="all, delete-orphan"
    )
    followups: Mapped[List["FollowupRecord"]] = relationship(
        back_populates="processing_run", cascade="all, delete-orphan"
    )


class ConceptRecord(Base):
    """
    Extracted concept stored for reference and linking.

    Concepts are extracted from content and stored both in PostgreSQL (for
    relational queries) and Neo4j (for graph traversal). This table provides
    the relational view.

    Attributes:
        id: Primary key UUID
        processing_run_id: Foreign key to processing run
        name: Concept name (indexed for lookup)
        definition: Clear definition
        context: How it's used in this content
        importance: core, supporting, tangential
        related_concepts: Names of related concepts
        embedding: Vector embedding for similarity search
        neo4j_node_id: ID of corresponding Neo4j node
    """

    __tablename__ = "concepts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    processing_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("processing_runs.id"), nullable=False
    )

    # Concept details
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    definition: Mapped[Optional[str]] = mapped_column(Text)
    context: Mapped[Optional[str]] = mapped_column(Text)
    importance: Mapped[str] = mapped_column(
        String(20), default=ConceptImportance.SUPPORTING.value
    )
    related_concepts: Mapped[Optional[list]] = mapped_column(ARRAY(String))

    # For similarity search (optional - primary storage in Neo4j)
    embedding: Mapped[Optional[list]] = mapped_column(ARRAY(Float))

    # Graph reference
    neo4j_node_id: Mapped[Optional[str]] = mapped_column(String(64))

    # Relationship
    processing_run: Mapped["ProcessingRun"] = relationship(back_populates="concepts")


class ConnectionRecord(Base):
    """
    Discovered connection to existing knowledge.

    Connections represent semantic relationships between content items
    discovered by the LLM processing pipeline.

    Attributes:
        id: Primary key UUID
        processing_run_id: Foreign key to processing run
        source_content_id: Content that was being processed
        target_content_id: Content that was connected to
        relationship_type: Type of relationship
        strength: Connection strength (0-1)
        explanation: Why these are connected
        verified_by_user: User confirmed this connection
    """

    __tablename__ = "connections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    processing_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("processing_runs.id"), nullable=False
    )

    # Connection endpoints
    source_content_id: Mapped[int] = mapped_column(
        ForeignKey("content.id"), nullable=False
    )
    target_content_id: Mapped[int] = mapped_column(
        ForeignKey("content.id"), nullable=False
    )
    target_title: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )  # Cached title for display without join

    # Connection details
    relationship_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # RELATES_TO, EXTENDS, CONTRADICTS, PREREQUISITE_FOR, APPLIES
    strength: Mapped[float] = mapped_column(Float, default=0.5)
    explanation: Mapped[Optional[str]] = mapped_column(Text)

    # User feedback
    verified_by_user: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationship
    processing_run: Mapped["ProcessingRun"] = relationship(back_populates="connections")


class QuestionRecord(Base):
    """
    Generated mastery question with spaced repetition state.

    Questions are generated to test understanding and integrated with
    the spaced repetition system for review scheduling.

    Attributes:
        id: Primary key UUID
        processing_run_id: Foreign key to processing run
        content_id: Content the question is about
        question: Question text
        question_type: conceptual, application, analysis, synthesis
        difficulty: foundational, intermediate, advanced
        hints: Progressive hints as array
        key_points: Key points for good answer
        next_review_at: When to show again (spaced repetition)
        review_count: Number of times reviewed
        ease_factor: SM-2 ease factor
    """

    __tablename__ = "mastery_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    processing_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("processing_runs.id"), nullable=False
    )
    content_id: Mapped[int] = mapped_column(ForeignKey("content.id"), nullable=False)

    # Question content
    question: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(
        String(30), default="conceptual"
    )  # conceptual, application, analysis, synthesis
    difficulty: Mapped[str] = mapped_column(
        String(20), default="intermediate"
    )  # foundational, intermediate, advanced
    hints: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    key_points: Mapped[Optional[list]] = mapped_column(ARRAY(String))

    # Spaced repetition state (timezone-aware UTC)
    next_review_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)

    # Timestamps (timezone-aware UTC)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )

    # Relationship
    processing_run: Mapped["ProcessingRun"] = relationship(back_populates="questions")


class FollowupRecord(Base):
    """
    Generated follow-up task.

    Follow-up tasks are actionable items generated from content to
    promote active learning.

    Attributes:
        id: Primary key UUID
        processing_run_id: Foreign key to processing run
        content_id: Content the task relates to
        task: Task description
        task_type: research, practice, connect, apply, review
        priority: high, medium, low
        estimated_time: 15min, 30min, 1hr, 2hr+
        completed: Whether task is done
        completed_at: When task was completed
    """

    __tablename__ = "followup_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    processing_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("processing_runs.id"), nullable=False
    )
    content_id: Mapped[int] = mapped_column(ForeignKey("content.id"), nullable=False)

    # Task details
    task: Mapped[str] = mapped_column(Text, nullable=False)
    task_type: Mapped[str] = mapped_column(
        String(30), default="research"
    )  # research, practice, connect, apply, review
    priority: Mapped[str] = mapped_column(
        String(10), default="medium"
    )  # high, medium, low
    estimated_time: Mapped[str] = mapped_column(
        String(20), default="30min"
    )  # 15min, 30min, 1hr, 2hr+

    # Completion tracking (timezone-aware UTC)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Timestamps (timezone-aware UTC)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )

    # Relationship
    processing_run: Mapped["ProcessingRun"] = relationship(back_populates="followups")


# Import Content model to set up relationship
# This is done at the bottom to avoid circular imports
from app.db.models import Content  # noqa: E402

# Add reverse relationship to Content model if not already present
if not hasattr(Content, "processing_runs"):
    Content.processing_runs = relationship(
        "ProcessingRun", back_populates="content", cascade="all, delete-orphan"
    )
