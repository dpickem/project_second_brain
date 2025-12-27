"""
SQLAlchemy Database Models

These models define the PostgreSQL schema for the Second Brain system.
They track content metadata, learning progress, and user interactions.

Tables:
- content: Ingested content (papers, articles, etc.)
- annotations: User annotations on content
- tags: Tag definitions
- content_tags: Many-to-many relationship
- practice_sessions: Learning sessions
- practice_attempts: Individual practice attempts
- spaced_rep_cards: Spaced repetition cards
- mastery_snapshots: Progress tracking
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
import enum


class ContentStatus(enum.Enum):
    """Status of content processing."""

    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class Content(Base):
    """
    Ingested content records.

    Tracks all content that has been ingested into the system,
    including papers, articles, books, code, and ideas.
    """

    __tablename__ = "content"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Content identification
    content_type: Mapped[str] = mapped_column(String(50))  # paper, article, book, etc.
    title: Mapped[str] = mapped_column(String(500))
    source_url: Mapped[Optional[str]] = mapped_column(String(2000))
    source_path: Mapped[Optional[str]] = mapped_column(
        String(1000)
    )  # Original file path

    # Obsidian integration
    vault_path: Mapped[Optional[str]] = mapped_column(
        String(1000)
    )  # Path in Obsidian vault

    # Processing
    status: Mapped[ContentStatus] = mapped_column(
        SQLEnum(ContentStatus), default=ContentStatus.PENDING
    )
    raw_text: Mapped[Optional[str]] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text)

    # Metadata
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON)  # Flexible metadata

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    annotations: Mapped[List["Annotation"]] = relationship(back_populates="content")
    cards: Mapped[List["SpacedRepCard"]] = relationship(back_populates="content")


class Annotation(Base):
    """
    User annotations on content.

    Stores highlights, notes, and other user-created annotations
    that are linked to specific content.
    """

    __tablename__ = "annotations"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("content.id"))

    # Annotation details
    annotation_type: Mapped[str] = mapped_column(
        String(50)
    )  # highlight, note, question
    text: Mapped[str] = mapped_column(Text)
    context: Mapped[Optional[str]] = mapped_column(Text)  # Surrounding text
    page_number: Mapped[Optional[int]] = mapped_column(Integer)

    # For handwritten notes (OCR)
    is_handwritten: Mapped[bool] = mapped_column(Boolean, default=False)
    ocr_confidence: Mapped[Optional[float]] = mapped_column(Float)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    content: Mapped["Content"] = relationship(back_populates="annotations")


class Tag(Base):
    """
    Tag definitions.

    Stores the controlled vocabulary of tags used across the system.
    Tags follow the domain/category/topic hierarchy.
    """

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True
    )  # e.g., "ml/transformers/attention"
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PracticeSession(Base):
    """
    Learning practice sessions.

    Groups practice attempts into sessions for tracking
    learning progress over time.
    """

    __tablename__ = "practice_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Session details
    session_type: Mapped[str] = mapped_column(String(50))  # review, quiz, exercise
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Stats
    total_cards: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    attempts: Mapped[List["PracticeAttempt"]] = relationship(back_populates="session")


class PracticeAttempt(Base):
    """
    Individual practice attempts within a session.

    Records each attempt at answering a question or completing
    an exercise during a practice session.
    """

    __tablename__ = "practice_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("practice_sessions.id"))
    card_id: Mapped[int] = mapped_column(ForeignKey("spaced_rep_cards.id"))

    # Attempt details
    response: Mapped[Optional[str]] = mapped_column(Text)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean)
    confidence: Mapped[Optional[int]] = mapped_column(Integer)  # 1-5 self-rating
    time_taken_seconds: Mapped[Optional[int]] = mapped_column(Integer)

    # Timestamps
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    session: Mapped["PracticeSession"] = relationship(back_populates="attempts")
    card: Mapped["SpacedRepCard"] = relationship(back_populates="attempts")


class SpacedRepCard(Base):
    """
    Spaced repetition cards.

    Cards are generated from content and used for spaced
    repetition learning. Uses a simplified SM-2 algorithm.
    """

    __tablename__ = "spaced_rep_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[Optional[int]] = mapped_column(ForeignKey("content.id"))

    # Card content
    card_type: Mapped[str] = mapped_column(String(50))  # concept, question, cloze
    front: Mapped[str] = mapped_column(Text)  # Question or prompt
    back: Mapped[str] = mapped_column(Text)  # Answer
    hints: Mapped[Optional[list]] = mapped_column(JSON)  # List of hints

    # Spaced repetition state (SM-2 algorithm)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    interval_days: Mapped[int] = mapped_column(Integer, default=1)
    repetitions: Mapped[int] = mapped_column(Integer, default=0)

    # Scheduling
    due_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_reviewed: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Stats
    total_reviews: Mapped[int] = mapped_column(Integer, default=0)
    correct_reviews: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    content: Mapped[Optional["Content"]] = relationship(back_populates="cards")
    attempts: Mapped[List["PracticeAttempt"]] = relationship(back_populates="card")


class MasterySnapshot(Base):
    """
    Progress tracking snapshots.

    Periodic snapshots of learning progress for analytics
    and visualization.
    """

    __tablename__ = "mastery_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Snapshot details
    snapshot_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    tag_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tags.id"))

    # Metrics
    total_cards: Mapped[int] = mapped_column(Integer, default=0)
    mastered_cards: Mapped[int] = mapped_column(Integer, default=0)
    learning_cards: Mapped[int] = mapped_column(Integer, default=0)
    new_cards: Mapped[int] = mapped_column(Integer, default=0)

    # Calculated mastery score (0-100)
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0)
