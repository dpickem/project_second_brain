"""
SQLAlchemy Database Models for the Learning System

These models support the FSRS-based spaced repetition system and
exercise-based active learning features.

Tables:
- practice_sessions: Learning sessions grouping practice attempts
- practice_attempts: Individual practice attempts for spaced rep cards
- spaced_rep_cards: Spaced repetition cards with FSRS algorithm
- mastery_snapshots: Progress tracking snapshots for analytics
- exercises: Generated exercises (free recall, code, debug, etc.)
- exercise_attempts: Learner attempts at exercises with evaluation results

ARCHITECTURE NOTE:
    This file contains SQLALCHEMY models for database persistence.
    There is a corresponding Pydantic file: app/models/learning.py

    Data flows: Service Layer → Pydantic → SQLAlchemy → Database
"""

from datetime import datetime, timezone
from typing import List, Optional
import uuid


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# ===========================================
# Practice Sessions & Attempts
# ===========================================


class PracticeSession(Base):
    """
    Learning practice sessions.

    Groups practice attempts into sessions for tracking
    learning progress over time.

    Attributes:
        id: Primary key, auto-incrementing integer identifier.
        session_type: Type of practice session (e.g., "review" for scheduled spaced
            repetition reviews, "quiz" for self-assessment, "exercise" for hands-on
            practice). Max 50 characters.
        started_at: Timestamp when the session began. Defaults to current time.
        ended_at: Timestamp when the session was completed. Null if session is
            still in progress or was abandoned.
        total_cards: Total number of cards presented during this session.
            Updated as cards are shown. Defaults to 0.
        correct_count: Number of cards answered correctly in this session.
            Used for calculating session accuracy. Defaults to 0.
        topics_covered: Array of topic tags covered in this session.
        exercise_count: Number of exercises completed in this session.
        average_score: Average score across exercises in this session.
        duration_minutes: Total duration of the session in minutes.
        attempts: List of individual PracticeAttempt records for each card
            reviewed in this session.
        exercise_attempts: List of ExerciseAttempt records for this session.
    """

    __tablename__ = "practice_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Session details
    session_type: Mapped[str] = mapped_column(String(50))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Stats
    total_cards: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)

    # Extended fields (added in migration 007)
    topics_covered: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    exercise_count: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    average_score: Mapped[Optional[float]] = mapped_column(Float)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)

    # Relationships
    attempts: Mapped[List["PracticeAttempt"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    exercise_attempts: Mapped[List["ExerciseAttempt"]] = relationship(
        back_populates="session"
    )


class PracticeAttempt(Base):
    """
    Individual practice attempts within a session.

    Records each attempt at answering a question or completing
    an exercise during a practice session.

    Attributes:
        id: Primary key, auto-incrementing integer identifier.
        session_id: Foreign key reference to the parent PracticeSession.
        card_id: Foreign key reference to the SpacedRepCard being practiced.
        response: User's response/answer to the card prompt. Optional, may be
            null for cards graded by self-assessment only.
        is_correct: Whether the attempt was marked as correct. Optional, may be
            null if not yet graded or for open-ended responses.
        confidence: User's self-reported confidence level (1-5 scale, where 1 is
            "complete guess" and 5 is "absolutely certain"). Used to calibrate
            spaced repetition intervals. Optional.
        time_taken_seconds: Time in seconds from card presentation to response
            submission. Useful for identifying struggling concepts. Optional.
        attempted_at: Timestamp when the attempt was recorded. Defaults to current time.
        session: Reference to the parent PracticeSession this attempt belongs to.
        card: Reference to the SpacedRepCard that was practiced.
    """

    __tablename__ = "practice_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("practice_sessions.id"))
    card_id: Mapped[int] = mapped_column(ForeignKey("spaced_rep_cards.id"))

    # Attempt details
    response: Mapped[Optional[str]] = mapped_column(Text)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean)
    confidence: Mapped[Optional[int]] = mapped_column(Integer)
    time_taken_seconds: Mapped[Optional[int]] = mapped_column(Integer)

    # Timestamps
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )

    # Relationships
    session: Mapped["PracticeSession"] = relationship(back_populates="attempts")
    card: Mapped["SpacedRepCard"] = relationship(back_populates="attempts")


# ===========================================
# Spaced Repetition Cards (FSRS)
# ===========================================


class SpacedRepCard(Base):
    """
    Spaced repetition cards with FSRS algorithm.

    Cards are generated from content and used for spaced
    repetition learning. Uses the FSRS-4.5 algorithm for scheduling.

    Attributes:
        id: Primary key, auto-incrementing integer identifier.
        content_id: Foreign key reference to source Content. Optional.
        card_type: Type of card (concept, question, cloze, code).
        front: Front side of the card - the question/prompt.
        back: Back side of the card - the answer.
        hints: JSON array of progressive hints.

        FSRS State:
        stability: Memory stability in days (FSRS).
        difficulty: Card difficulty 0-1 (FSRS).
        state: Card state (new, learning, review, relearning).
        lapses: Number of times the card was forgotten.
        scheduled_days: Days until next review.

        Scheduling:
        due_date: When card is next due for review.
        last_reviewed: Timestamp of most recent review.

        Stats:
        total_reviews: Total review count.
        correct_reviews: Correct review count.

        Code card fields:
        language: Programming language.
        starter_code: Initial code template.
        solution_code: Reference solution.
        test_cases: Test case definitions.

        Metadata:
        tags: Topic tags for filtering.
        concept_id: Related Neo4j concept ID.

        Relationships:
        content: Source Content this card was generated from.
        attempts: All PracticeAttempt records for this card.
    """

    __tablename__ = "spaced_rep_cards"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Content reference - two fields for different use cases:
    # 1. content_id (str): UUID string - the app-facing identifier, used everywhere
    # 2. source_content_pk (int FK): Database FK for ORM relationship only
    content_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    source_content_pk: Mapped[Optional[int]] = mapped_column(
        ForeignKey("content.id"), index=True
    )

    # Card content
    card_type: Mapped[str] = mapped_column(String(50))
    front: Mapped[str] = mapped_column(Text)
    back: Mapped[str] = mapped_column(Text)
    hints: Mapped[Optional[list]] = mapped_column(JSON)

    # FSRS state
    stability: Mapped[float] = mapped_column(Float, default=0.0)
    difficulty: Mapped[float] = mapped_column(Float, default=0.3)
    state: Mapped[str] = mapped_column(String(20), default="new")
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    scheduled_days: Mapped[int] = mapped_column(Integer, default=0)
    repetitions: Mapped[int] = mapped_column(
        Integer, default=0
    )  # Consecutive successful reviews

    # Scheduling
    due_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )
    last_reviewed: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Stats
    total_reviews: Mapped[int] = mapped_column(Integer, default=0)
    correct_reviews: Mapped[int] = mapped_column(Integer, default=0)

    # Code card fields (added in migration 007)
    language: Mapped[Optional[str]] = mapped_column(String(50))
    starter_code: Mapped[Optional[str]] = mapped_column(Text)
    solution_code: Mapped[Optional[str]] = mapped_column(Text)
    test_cases: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Metadata (added in migration 007)
    tags: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    concept_id: Mapped[Optional[str]] = mapped_column(String(64))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )

    # Relationships
    content: Mapped[Optional["Content"]] = relationship(back_populates="cards")
    attempts: Mapped[List["PracticeAttempt"]] = relationship(back_populates="card")
    review_history: Mapped[List["CardReviewHistory"]] = relationship(
        back_populates="card"
    )


# ===========================================
# Card Review History
# ===========================================


class CardReviewHistory(Base):
    """
    Historical record of individual card reviews.

    Each time a card is reviewed, a record is created here to track
    review activity over time for analytics and learning curves.

    Attributes:
        id: Primary key, auto-incrementing integer identifier.
        card_id: Foreign key reference to the reviewed SpacedRepCard.
        rating: FSRS rating (1=Again, 2=Hard, 3=Good, 4=Easy).
        reviewed_at: Timestamp when the review occurred.
        time_spent_seconds: Optional time spent on the review.
        state_before: Card state before the review.
        state_after: Card state after the review.
        stability_after: Card stability after the review.
        scheduled_days: Days until next review after this review.
    """

    __tablename__ = "card_review_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("spaced_rep_cards.id"), index=True)

    # Review details
    rating: Mapped[int] = mapped_column(Integer)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, index=True
    )
    time_spent_seconds: Mapped[Optional[int]] = mapped_column(Integer)

    # State tracking
    state_before: Mapped[Optional[str]] = mapped_column(String(20))
    state_after: Mapped[Optional[str]] = mapped_column(String(20))
    stability_after: Mapped[Optional[float]] = mapped_column(Float)
    scheduled_days: Mapped[Optional[int]] = mapped_column(Integer)

    # Relationship
    card: Mapped["SpacedRepCard"] = relationship(back_populates="review_history")


# ===========================================
# Mastery Tracking
# ===========================================


class MasterySnapshot(Base):
    """
    Progress tracking snapshots.

    Periodic snapshots of learning progress for analytics
    and visualization.

    Attributes:
        id: Primary key, auto-incrementing integer identifier.
        snapshot_date: Timestamp when this snapshot was captured.
        tag_id: Foreign key reference to Tag for topic-specific snapshots.
        topic_path: Topic path string (e.g., "ml/transformers").
        total_cards: Total number of cards in scope at snapshot time.
        mastered_cards: Cards with stability >= 21 days.
        learning_cards: Cards actively being learned.
        new_cards: Cards never reviewed.
        mastery_score: Calculated mastery percentage (0-1).
        practice_count: Total practice attempts for this topic.
        success_rate: Correct attempts / total attempts.
        trend: Mastery trend (improving, stable, declining).
        last_practiced: Timestamp of last practice for this topic.
        retention_estimate: Estimated current retention.
        days_since_review: Days since last review.
    """

    __tablename__ = "mastery_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Snapshot details
    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )
    tag_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tags.id"))

    # Topic tracking (added in migration 007)
    topic_path: Mapped[Optional[str]] = mapped_column(String(200), index=True)

    # Card counts
    total_cards: Mapped[int] = mapped_column(Integer, default=0)
    mastered_cards: Mapped[int] = mapped_column(Integer, default=0)
    learning_cards: Mapped[int] = mapped_column(Integer, default=0)
    new_cards: Mapped[int] = mapped_column(Integer, default=0)

    # Mastery metrics
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Extended metrics (added in migration 007)
    practice_count: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    success_rate: Mapped[Optional[float]] = mapped_column(Float)
    trend: Mapped[Optional[str]] = mapped_column(String(20))
    last_practiced: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    retention_estimate: Mapped[Optional[float]] = mapped_column(Float)
    days_since_review: Mapped[Optional[int]] = mapped_column(Integer)


# ===========================================
# Exercises
# ===========================================


class Exercise(Base):
    """
    Generated exercise for active learning.

    Exercises are created by the LLM exercise generator and adapted based
    on the learner's mastery level. Different exercise types support
    different learning strategies (worked examples for novices,
    free recall for intermediates, etc.).

    Attributes:
        id: Primary key, auto-incrementing integer
        exercise_uuid: Unique UUID for external reference
        exercise_type: Type of exercise (free_recall, code_implement, etc.)
        topic: Topic path (e.g., "ml/transformers/attention")
        difficulty: Difficulty level (foundational, intermediate, advanced)
        prompt: Main exercise prompt/question
        hints: Progressive hints array
        expected_key_points: Key points a good answer should cover
        worked_example: For worked_example type - step-by-step solution
        follow_up_problem: Follow-up problem after worked example
        language: Programming language for code exercises
        starter_code: Initial code template
        solution_code: Reference solution
        test_cases: JSON array of test case definitions
        buggy_code: Code with intentional bugs for debug exercises
        source_content_ids: Content IDs this exercise was generated from
        estimated_time_minutes: Estimated completion time
        tags: Topic tags for categorization
        created_at: Creation timestamp
        updated_at: Last update timestamp
        attempts: Related exercise attempts
    """

    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    exercise_uuid: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
    )

    # Exercise classification
    exercise_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # free_recall, self_explain, worked_example, code_implement, code_debug, etc.
    topic: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    difficulty: Mapped[str] = mapped_column(
        String(20), nullable=False, default="intermediate"
    )  # foundational, intermediate, advanced

    # Core content
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    hints: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    expected_key_points: Mapped[Optional[list]] = mapped_column(ARRAY(String))

    # For worked examples
    worked_example: Mapped[Optional[str]] = mapped_column(Text)
    follow_up_problem: Mapped[Optional[str]] = mapped_column(Text)

    # For code exercises
    language: Mapped[Optional[str]] = mapped_column(String(50))
    starter_code: Mapped[Optional[str]] = mapped_column(Text)
    solution_code: Mapped[Optional[str]] = mapped_column(Text)
    test_cases: Mapped[Optional[dict]] = mapped_column(JSONB)

    # For debugging exercises
    buggy_code: Mapped[Optional[str]] = mapped_column(Text)

    # Source and metadata
    source_content_ids: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    estimated_time_minutes: Mapped[int] = mapped_column(Integer, default=10)
    tags: Mapped[Optional[list]] = mapped_column(ARRAY(String))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now
    )

    # Relationships
    attempts: Mapped[List["ExerciseAttempt"]] = relationship(
        back_populates="exercise", cascade="all, delete-orphan"
    )


class ExerciseAttempt(Base):
    """
    Record of a learner's attempt at an exercise.

    Tracks the response, evaluation results, and learning metrics
    for each exercise attempt. Supports both text and code responses.

    Attributes:
        id: Primary key
        attempt_uuid: Unique UUID for external reference
        session_id: Optional link to practice session
        exercise_id: Foreign key to exercise
        response: Text response for non-code exercises
        response_code: Code response for code exercises
        score: Normalized score (0-1)
        is_correct: Whether attempt was considered correct (score >= threshold)
        feedback: LLM-generated feedback
        covered_points: Key points that were addressed
        missing_points: Key points that were missed
        misconceptions: Identified misconceptions with corrections
        tests_passed: Number of passing tests (code exercises)
        tests_total: Total number of tests (code exercises)
        test_results: Detailed test results JSON
        execution_error: Error message if code execution failed
        confidence_before: Self-reported confidence before attempting (1-5)
        confidence_after: Self-reported confidence after feedback (1-5)
        time_spent_seconds: Time spent on the exercise
        attempted_at: Timestamp of attempt
        session: Related practice session
        exercise: Related exercise
    """

    __tablename__ = "exercise_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_uuid: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
    )

    # Links
    session_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("practice_sessions.id"), index=True
    )
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id"), nullable=False, index=True
    )

    # Response content
    response: Mapped[Optional[str]] = mapped_column(Text)
    response_code: Mapped[Optional[str]] = mapped_column(Text)

    # Evaluation results
    score: Mapped[Optional[float]] = mapped_column(Float)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean)
    feedback: Mapped[Optional[str]] = mapped_column(Text)

    # Detailed evaluation
    covered_points: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    missing_points: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    misconceptions: Mapped[Optional[list]] = mapped_column(ARRAY(String))

    # Code evaluation results
    tests_passed: Mapped[Optional[int]] = mapped_column(Integer)
    tests_total: Mapped[Optional[int]] = mapped_column(Integer)
    test_results: Mapped[Optional[dict]] = mapped_column(JSONB)
    execution_error: Mapped[Optional[str]] = mapped_column(Text)

    # Confidence tracking
    confidence_before: Mapped[Optional[int]] = mapped_column(Integer)
    confidence_after: Mapped[Optional[int]] = mapped_column(Integer)

    # Timing
    time_spent_seconds: Mapped[Optional[int]] = mapped_column(Integer)

    # Timestamps
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )

    # Relationships
    session: Mapped[Optional["PracticeSession"]] = relationship(
        back_populates="exercise_attempts"
    )
    exercise: Mapped["Exercise"] = relationship(back_populates="attempts")


# ===========================================
# Learning Time Tracking
# ===========================================


class LearningTimeLog(Base):
    """
    Tracks time spent on learning activities.

    Logged automatically when:
    - Practice sessions end (session duration)
    - Review sessions end (time on cards)
    - Content is read (if frontend tracks)
    - Exercises are completed

    Attributes:
        id: Primary key, auto-incrementing integer identifier.
        topic: Topic being learned (e.g., "ml/transformers").
        content_id: Optional FK to content being studied.
        activity_type: Type of activity (review, practice, reading, exercise).
        started_at: When the activity started.
        ended_at: When the activity ended.
        duration_seconds: Duration in seconds.
        items_completed: Number of items completed (cards, exercises, etc.).
        session_id: Optional FK to practice session.
    """

    __tablename__ = "learning_time_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # What was being learned
    topic: Mapped[Optional[str]] = mapped_column(String(200), index=True)
    content_id: Mapped[Optional[int]] = mapped_column(ForeignKey("content.id"))

    # Activity type
    activity_type: Mapped[str] = mapped_column(String(50), index=True)

    # Time tracking
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int] = mapped_column(Integer)

    # Metadata
    items_completed: Mapped[int] = mapped_column(Integer, default=0)
    session_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("practice_sessions.id")
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )


# ===========================================
# Forward Reference for Content relationship
# ===========================================

# Import Content to set up relationships at module load time
# This is done at the bottom to avoid circular imports
from app.db.models import Content  # noqa: E402, F401
