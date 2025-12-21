# Data Models Design

> **Document Status**: Design Specification  
> **Last Updated**: December 2025  
> **Related Docs**: `06_backend_api.md`, `04_knowledge_graph_neo4j.md`

---

## 1. Overview

This document defines the Pydantic models for API request/response validation and SQLAlchemy models for PostgreSQL persistence. These models form the backbone of data interchange throughout the Second Brain system.

### 1.1 Source of Truth: Obsidian Notes

**Obsidian is the canonical source of truth** for all knowledge content in this system. Every piece of content—whether ingested from papers, articles, books, or captured ideas—ultimately manifests as a Markdown note in the Obsidian vault. The databases (PostgreSQL, Neo4j) serve as derived indexes that enhance queryability, enable semantic search, and track learning progress, but the authoritative content always lives in Obsidian.

This design principle ensures:
- **Portability**: Your knowledge base remains human-readable Markdown files you own
- **Durability**: No vendor lock-in; the vault works offline without any backend services
- **Transparency**: You can always inspect, edit, or reorganize your notes directly
- **Recoverability**: The databases can be rebuilt from the Obsidian vault at any time

### 1.2 Unique Identifiers

**Every entity in the system must have a globally unique identifier (UUID v4)**. This applies to:
- Content items (papers, articles, notes)
- Annotations and highlights
- Concepts and topics in the knowledge graph
- Practice exercises and sessions
- Spaced repetition cards
- All database records

UUIDs are stored in Obsidian note frontmatter (YAML) to maintain bidirectional linking between the vault and databases:

```yaml
---
id: "550e8400-e29b-41d4-a716-446655440000"
type: paper
title: "Attention Is All You Need"
created: 2025-12-20T10:30:00Z
---
```

This ensures that even if a note is moved or renamed in Obsidian, its identity remains stable and all relationships in the knowledge graph stay intact.

---

## 2. Pydantic Models

Pydantic models provide runtime validation, serialization, and documentation for all API interactions. They enforce type safety at the boundaries of the system and generate OpenAPI schemas automatically.

### 2.1 Content Models

Content models represent ingested source materials and their annotations. These models handle the diverse range of input types—from academic papers to voice memos—and normalize them into a unified structure for processing.

The `UnifiedContent` model is the primary representation that flows through the ingestion pipeline. Each content item receives a UUID upon creation that persists throughout its lifecycle and links back to the corresponding Obsidian note.

```python
# backend/app/models/content.py

from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional

class ContentType(str, Enum):
    """
    Categorizes the origin/format of ingested content.
    Each type may have specialized processing pipelines.
    """
    PAPER = "paper"          # Academic papers (PDF, arXiv)
    ARTICLE = "article"      # Web articles, blog posts
    BOOK = "book"            # Book chapters or full books
    CODE = "code"            # Code repositories, snippets
    IDEA = "idea"            # Quick capture, fleeting notes
    VOICE_MEMO = "voice_memo"  # Transcribed audio recordings

class AnnotationType(str, Enum):
    """
    Types of annotations that can be extracted from source documents.
    The ingestion pipeline attempts to preserve all user annotations.
    """
    DIGITAL_HIGHLIGHT = "digital_highlight"    # PDF highlights, Kindle highlights
    HANDWRITTEN_NOTE = "handwritten_note"      # OCR'd handwritten annotations
    TYPED_COMMENT = "typed_comment"            # Margin notes, comments
    DIAGRAM = "diagram"                        # Extracted diagrams/figures

class Annotation(BaseModel):
    """
    Represents a single annotation extracted from source content.
    Annotations are linked to their source and may include positional data
    for reconstructing the original reading context.
    """
    id: str = Field(..., description="Unique identifier (UUID v4) for this annotation")
    type: AnnotationType
    content: str = Field(..., description="The text or description of the annotation")
    page_number: Optional[int] = Field(None, description="Page number in source document")
    position: Optional[dict] = Field(None, description="Bounding box or location coordinates")
    context: Optional[str] = Field(None, description="Surrounding text for context")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="OCR/extraction confidence score")

class UnifiedContent(BaseModel):
    """
    Canonical representation of any ingested content.
    
    This model normalizes diverse input types into a consistent structure.
    The `id` field matches the UUID stored in the corresponding Obsidian note's
    frontmatter, establishing the link between database records and the source of truth.
    """
    id: str = Field(..., description="Unique identifier (UUID v4), matches Obsidian frontmatter id")
    source_type: ContentType
    source_url: Optional[str] = Field(None, description="Original URL if web-sourced")
    source_file_path: Optional[str] = Field(None, description="Original file path if locally sourced")
    title: str = Field(..., max_length=500)
    authors: list[str] = Field(default_factory=list)
    created_at: datetime = Field(..., description="Original creation/publication date")
    ingested_at: datetime = Field(..., description="When this was added to the system")
    full_text: str = Field(..., description="Extracted full text content")
    annotations: list[Annotation] = Field(default_factory=list)
    raw_file_hash: Optional[str] = Field(None, description="SHA-256 hash for deduplication")
    asset_paths: list[str] = Field(default_factory=list, description="Paths to extracted images/assets")
    processing_status: str = Field(default="pending", description="pending|processing|completed|failed")
    obsidian_path: Optional[str] = Field(None, description="Path to note in Obsidian vault (source of truth)")

class CaptureResponse(BaseModel):
    """Response returned after successfully capturing new content."""
    status: str
    id: str = Field(..., description="UUID of the created content item")
    message: Optional[str] = None
    obsidian_path: Optional[str] = Field(None, description="Path where Obsidian note was created")

class ProcessingStatus(BaseModel):
    """Tracks the state of async content processing jobs."""
    id: str = Field(..., description="UUID of the content being processed")
    status: str  # pending, processing, completed, failed
    progress: Optional[float] = Field(None, ge=0, le=1, description="0.0 to 1.0 completion")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime
    updated_at: datetime
```

### 2.2 Practice Models

Practice models support the active learning system, which generates exercises based on your knowledge graph and tracks your responses. These models implement evidence-based learning techniques including free recall, self-explanation, and spaced repetition.

Each exercise and card maintains a UUID that links to the source concepts in the knowledge graph, enabling the system to identify weak spots and suggest targeted review.

```python
# backend/app/models/practice.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum

class ExerciseType(str, Enum):
    """
    Types of practice exercises, each targeting different cognitive processes.
    Based on cognitive science research on effective learning.
    """
    # Knowledge-based exercises
    FREE_RECALL = "free_recall"        # Write everything you remember about a topic
    SELF_EXPLAIN = "self_explain"      # Explain a concept in your own words
    WORKED_EXAMPLE = "worked_example"  # Step through a problem with guidance
    APPLICATION = "application"        # Apply concepts to novel scenarios
    COMPARE_CONTRAST = "compare_contrast"  # Analyze similarities/differences
    
    # Coding exercises
    CODE_IMPLEMENTATION = "code_implementation"  # Implement function/class from requirements
    CODE_COMPLETION = "code_completion"          # Fill in missing parts of code
    BUG_FIX = "bug_fix"                          # Find and fix bugs in provided code
    CODE_REVIEW = "code_review"                  # Identify issues/improvements in code
    CODE_TRACE = "code_trace"                    # Predict output by tracing execution
    REFACTOR = "refactor"                        # Improve code quality without changing behavior

class Exercise(BaseModel):
    """
    A generated practice exercise targeting specific concepts.
    
    Exercises are dynamically generated based on the user's knowledge graph
    and learning history. The `id` is unique per generation; regenerating
    an exercise creates a new UUID.
    
    For coding exercises, additional fields like `starter_code`, `test_cases`,
    and `language` provide the scaffolding needed for code-based practice.
    """
    id: str = Field(..., description="Unique identifier (UUID v4) for this exercise instance")
    exercise_type: ExerciseType
    topic: str = Field(..., description="Topic path (e.g., 'ml/transformers/attention')")
    difficulty: str = Field(..., description="foundational|intermediate|advanced")
    prompt: str = Field(..., description="The exercise question or instruction")
    hints: list[str] = Field(default_factory=list, description="Progressive hints if user struggles")
    expected_key_points: list[str] = Field(default_factory=list, description="Points a good answer should cover")
    worked_example: Optional[str] = Field(None, description="Step-by-step solution for worked example type")
    estimated_time_minutes: int = Field(default=15, ge=1, le=120)
    source_concept_ids: list[str] = Field(default_factory=list, description="UUIDs of concepts being tested")
    
    # Coding exercise fields (used when exercise_type is a coding type)
    language: Optional[str] = Field(None, description="Programming language (e.g., 'python', 'typescript')")
    starter_code: Optional[str] = Field(None, description="Initial code for completion/bug_fix/review/trace exercises")
    test_cases: list[dict] = Field(default_factory=list, description="Test cases for validating implementations: [{input, expected_output}]")
    expected_output: Optional[str] = Field(None, description="Expected output for code_trace exercises")
    solution_code: Optional[str] = Field(None, description="Reference solution (revealed after attempt)")

class ExerciseResponse(BaseModel):
    """User's response to a practice exercise."""
    response: str = Field(..., description="User's written answer")
    time_spent_seconds: int = Field(..., ge=0)
    confidence: float = Field(..., ge=1, le=5, description="Self-reported confidence (1-5 scale)")

class EvaluationResult(BaseModel):
    """
    LLM-generated evaluation of a practice response.
    Identifies gaps and misconceptions to guide further study.
    
    For coding exercises, includes additional fields for test results
    and code quality feedback.
    """
    score: float = Field(..., ge=0, le=1, description="Overall score (0.0 to 1.0)")
    covered_points: list[dict] = Field(..., description="Key points successfully addressed")
    missing_points: list[str] = Field(..., description="Important points not mentioned")
    misconceptions: list[str] = Field(..., description="Identified incorrect understandings")
    feedback: str = Field(..., description="Constructive feedback for improvement")
    suggested_review: list[str] = Field(..., description="Concept UUIDs to review")
    
    # Coding exercise evaluation fields
    tests_passed: Optional[int] = Field(None, description="Number of test cases passed")
    tests_total: Optional[int] = Field(None, description="Total number of test cases")
    test_results: list[dict] = Field(default_factory=list, description="Per-test results: [{name, passed, input, expected, actual}]")
    code_quality_notes: list[str] = Field(default_factory=list, description="Style, efficiency, and best practice observations")
    execution_error: Optional[str] = Field(None, description="Runtime/syntax error if code failed to execute")

class Rating(int, Enum):
    """FSRS-style rating for spaced repetition reviews."""
    AGAIN = 1  # Complete failure, reset interval
    HARD = 2   # Correct but difficult, shorter interval
    GOOD = 3   # Correct with expected effort
    EASY = 4   # Correct with minimal effort, longer interval

class SpacedRepCard(BaseModel):
    """
    A spaced repetition flashcard using the FSRS algorithm.
    
    Cards are derived from concepts in the knowledge graph. The `context_note_id`
    links back to the Obsidian note containing the source material.
    """
    id: str = Field(..., description="Unique identifier (UUID v4) for this card")
    card_type: str = Field(..., description="basic|cloze|concept|connection")
    front: str = Field(..., description="Question or prompt side")
    back: str = Field(..., description="Answer side")
    context_note_id: Optional[str] = Field(None, description="UUID of source Obsidian note")
    tags: list[str] = Field(default_factory=list)
    # FSRS algorithm parameters
    difficulty: float = Field(default=0.3, ge=0, le=1, description="Card difficulty (D parameter)")
    stability: float = Field(default=1.0, ge=0, description="Memory stability in days (S parameter)")
    due_date: Optional[datetime] = Field(None, description="Next scheduled review date")
    last_review: Optional[datetime] = None
    review_count: int = Field(default=0, ge=0)
    lapses: int = Field(default=0, ge=0, description="Number of times forgotten")

class CardReview(BaseModel):
    """Records a single review of a spaced repetition card."""
    rating: Rating
    response_time_ms: int = Field(..., ge=0, description="Time taken to respond")

class PracticeSession(BaseModel):
    """
    A timed practice session combining exercises and card reviews.
    Sessions group related practice activities for analytics tracking.
    """
    id: str = Field(..., description="Unique identifier (UUID v4) for this session")
    items: list[dict] = Field(..., description="Ordered list of exercises/cards in session")
    estimated_duration: int = Field(..., description="Expected duration in minutes")
    created_at: datetime
    status: str = Field(default="active", description="active|completed|abandoned")
```

### 2.3 Analytics Models

Analytics models aggregate learning data to provide insights into mastery progression and identify areas needing attention. These power the dashboard visualizations and recommendation engine.

All analytics are derived from practice attempts and card reviews, which themselves link back to concepts and Obsidian notes via UUIDs.

```python
# backend/app/models/analytics.py

from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

class MasteryScore(BaseModel):
    """
    Mastery assessment for a single topic.
    Computed from practice performance and review history.
    """
    topic: str = Field(..., description="Topic path (e.g., 'ml/transformers')")
    score: float = Field(..., ge=0, le=1, description="Mastery score (0.0 to 1.0)")
    practice_count: int = Field(..., ge=0, description="Total practice attempts")
    last_practiced: Optional[date] = None
    trend: str = Field(..., description="improving|stable|declining")
    concept_count: int = Field(default=0, description="Number of concepts in this topic")

class MasteryOverview(BaseModel):
    """
    High-level summary of knowledge mastery across all topics.
    Used for dashboard overview displays.
    """
    overall_score: float = Field(..., ge=0, le=1)
    topics: list[MasteryScore] = Field(default_factory=list)
    total_concepts: int = Field(..., ge=0, description="Total concepts in knowledge graph")
    mastered_count: int = Field(..., ge=0, description="Concepts with score >= 0.8")
    learning_count: int = Field(default=0, description="Concepts actively being learned")
    new_count: int = Field(default=0, description="Concepts not yet practiced")

class WeakSpot(BaseModel):
    """
    Identifies a topic or concept requiring additional attention.
    Used by the recommendation engine to suggest review priorities.
    """
    topic: str
    concept_id: Optional[str] = Field(None, description="UUID of specific weak concept, if applicable")
    mastery_score: float = Field(..., ge=0, le=1)
    success_rate: float = Field(..., ge=0, le=1, description="Recent practice success rate")
    trend: str = Field(..., description="improving|stable|declining")
    days_since_practice: int = Field(..., ge=0)
    recommendation: str = Field(..., description="Suggested action to improve")

class LearningCurvePoint(BaseModel):
    """Single data point in a learning curve visualization."""
    date: date
    accuracy: float = Field(..., ge=0, le=1)
    confidence: float = Field(..., ge=0, le=1)
    practice_count: int = Field(..., ge=0)

class LearningCurve(BaseModel):
    """
    Time-series data showing mastery progression for a topic.
    Enables visualization of learning velocity and plateaus.
    """
    topic: Optional[str] = Field(None, description="Topic path, or None for overall")
    data_points: list[LearningCurvePoint] = Field(default_factory=list)
    trend: str = Field(..., description="improving|stable|declining|insufficient_data")

class StreakData(BaseModel):
    """
    Gamification data tracking practice consistency.
    Encourages daily engagement with the learning system.
    """
    current_streak: int = Field(..., ge=0, description="Consecutive days practiced")
    longest_streak: int = Field(..., ge=0, description="All-time best streak")
    total_practice_days: int = Field(..., ge=0, description="Total unique days with practice")
    calendar: dict[str, int] = Field(default_factory=dict, description="ISO date -> practice count")
```

---

## 3. SQLAlchemy Models

SQLAlchemy models define the PostgreSQL schema for persistent storage. PostgreSQL serves as the **operational database** for fast queries, practice scheduling, and analytics aggregation, while Obsidian remains the source of truth for content.

All tables use UUID primary keys that correspond to identifiers in Obsidian note frontmatter, enabling bidirectional synchronization.

### 3.1 Core Tables

Core tables store content metadata and annotations. The `obsidian_path` column maintains the critical link to the source-of-truth Markdown files.

```python
# backend/app/db/models.py

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class Content(Base):
    """
    Stores metadata for ingested content items.
    
    The `id` matches the UUID in the corresponding Obsidian note's frontmatter.
    The `obsidian_path` points to the source-of-truth Markdown file.
    If conflicts arise, the Obsidian note takes precedence.
    """
    __tablename__ = "content"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
                comment="UUID matching Obsidian frontmatter id")
    source_type = Column(String(50), nullable=False,
                        comment="paper|article|book|code|idea|voice_memo")
    source_url = Column(Text, comment="Original URL if web-sourced")
    source_file_path = Column(Text, comment="Original file path if locally sourced")
    title = Column(String(500), nullable=False)
    authors = Column(ARRAY(String), comment="List of author names")
    created_at = Column(DateTime, nullable=False, comment="Original creation/publication date")
    ingested_at = Column(DateTime, default=datetime.utcnow)
    full_text = Column(Text, comment="Extracted full text (may be truncated)")
    raw_file_hash = Column(String(64), comment="SHA-256 for deduplication")
    processing_status = Column(String(20), default="pending",
                              comment="pending|processing|completed|failed")
    obsidian_path = Column(Text, nullable=False,
                          comment="Path to source-of-truth Obsidian note")
    
    annotations = relationship("Annotation", back_populates="content", cascade="all, delete-orphan")

class Annotation(Base):
    """
    Stores annotations/highlights extracted from source documents.
    
    Each annotation has its own UUID and links to its parent content.
    Annotations may also be represented as separate Obsidian notes or
    as blocks within the parent content's note.
    """
    __tablename__ = "annotations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
                comment="Unique annotation identifier")
    content_id = Column(UUID(as_uuid=True), ForeignKey("content.id"), nullable=False)
    type = Column(String(50), nullable=False,
                 comment="digital_highlight|handwritten_note|typed_comment|diagram")
    text = Column(Text, nullable=False, comment="Annotation content")
    page_number = Column(Integer, comment="Page in source document")
    position = Column(JSON, comment="Bounding box or coordinates")
    context = Column(Text, comment="Surrounding text for context")
    confidence = Column(Float, comment="OCR/extraction confidence 0.0-1.0")
    obsidian_block_id = Column(String(50), comment="Block reference in Obsidian note")
    
    content = relationship("Content", back_populates="annotations")
```

### 3.2 Practice Tables

Practice tables track learning activities and spaced repetition scheduling. These tables support the FSRS algorithm and enable analytics on learning progress.

The `context_note_id` in cards and `concept_id` in attempts link practice activities back to specific Obsidian notes and knowledge graph concepts.

```python
class PracticeSession(Base):
    """
    Groups related practice activities for a single study session.
    
    Sessions have their own UUIDs and aggregate exercises and card reviews
    to enable session-level analytics and resume capability.
    """
    __tablename__ = "practice_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
                comment="Unique session identifier")
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, comment="Null if session still active")
    topics = Column(JSON, comment="Topic paths covered in this session")
    exercise_count = Column(Integer, default=0)
    card_count = Column(Integer, default=0, comment="Spaced rep cards reviewed")
    status = Column(String(20), default="active",
                   comment="active|completed|abandoned")
    
    attempts = relationship("PracticeAttempt", back_populates="session", cascade="all, delete-orphan")

class PracticeAttempt(Base):
    """
    Records a single practice exercise attempt with evaluation.
    
    Links to the concept being practiced via `concept_id`, which corresponds
    to a Concept node in Neo4j and/or an Obsidian note UUID.
    """
    __tablename__ = "practice_attempts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
                comment="Unique attempt identifier")
    session_id = Column(UUID(as_uuid=True), ForeignKey("practice_sessions.id"))
    concept_id = Column(UUID(as_uuid=True), comment="UUID of concept being tested")
    exercise_type = Column(String(50), comment="free_recall|self_explain|code_implementation|bug_fix|etc")
    prompt = Column(Text, nullable=False, comment="Exercise question/instruction")
    response = Column(Text, comment="User's answer")
    time_spent_seconds = Column(Integer)
    score = Column(Float, comment="Evaluation score 0.0-1.0")
    is_correct = Column(Boolean, comment="Binary correctness for simple exercises")
    confidence_before = Column(Float, comment="Self-reported confidence before (1-5)")
    confidence_after = Column(Float, comment="Self-reported confidence after (1-5)")
    feedback = Column(Text, comment="LLM-generated feedback")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("PracticeSession", back_populates="attempts")

class SpacedRepCard(Base):
    """
    A spaced repetition flashcard with FSRS scheduling parameters.
    
    The `id` is the card's unique identifier. The `context_note_id` links
    to the Obsidian note from which this card was derived, maintaining
    traceability to the source of truth.
    """
    __tablename__ = "spaced_rep_cards"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
                comment="Unique card identifier")
    card_type = Column(String(50), nullable=False, comment="basic|cloze|concept|connection")
    front = Column(Text, nullable=False, comment="Question/prompt side")
    back = Column(Text, nullable=False, comment="Answer side")
    context_note_id = Column(UUID(as_uuid=True), 
                            comment="UUID of source Obsidian note")
    tags = Column(JSON, default=[], comment="Topic tags for filtering")
    # FSRS algorithm state
    difficulty = Column(Float, default=0.3, comment="D parameter (0.0-1.0)")
    stability = Column(Float, default=1.0, comment="S parameter (days)")
    due_date = Column(DateTime, comment="Next scheduled review")
    last_review = Column(DateTime)
    review_count = Column(Integer, default=0)
    lapses = Column(Integer, default=0, comment="Times forgotten after learning")
    created_at = Column(DateTime, default=datetime.utcnow)
    suspended = Column(Boolean, default=False, comment="Temporarily exclude from reviews")

class CardReview(Base):
    """
    Records individual card review events for analytics and algorithm tuning.
    """
    __tablename__ = "card_reviews"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_id = Column(UUID(as_uuid=True), ForeignKey("spaced_rep_cards.id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("practice_sessions.id"))
    rating = Column(Integer, nullable=False, comment="1=Again, 2=Hard, 3=Good, 4=Easy")
    response_time_ms = Column(Integer, comment="Time to respond")
    reviewed_at = Column(DateTime, default=datetime.utcnow)
    # Snapshot of card state at review time for algorithm analysis
    difficulty_before = Column(Float)
    stability_before = Column(Float)
    difficulty_after = Column(Float)
    stability_after = Column(Float)

class MasterySnapshot(Base):
    """
    Point-in-time snapshot of mastery for analytics and trend detection.
    
    Snapshots are taken periodically (e.g., daily) to track learning
    progress over time without expensive real-time aggregation.
    """
    __tablename__ = "mastery_snapshots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concept_id = Column(UUID(as_uuid=True), comment="UUID of concept, if concept-level snapshot")
    topic_path = Column(String(255), comment="Topic path for topic-level snapshots")
    mastery_score = Column(Float, comment="Computed mastery 0.0-1.0")
    confidence_avg = Column(Float, comment="Average self-reported confidence")
    practice_count = Column(Integer, comment="Total practices at snapshot time")
    success_rate = Column(Float, comment="Recent success rate")
    snapshot_date = Column(DateTime, nullable=False)
```

---

## 4. Neo4j Node Schemas

Neo4j stores the knowledge graph with concepts, sources, and their relationships. Each node's `id` property is a UUID that matches identifiers in PostgreSQL and Obsidian frontmatter, ensuring consistency across all storage layers.

The `obsidian_path` property on Source nodes provides direct linkage to the source-of-truth Markdown files.

```python
# Graph node structures (for reference)
# These are not Python classes but document the expected node properties

SOURCE_NODE = {
    "id": "uuid",                    # Matches Obsidian frontmatter id and PostgreSQL
    "type": "paper|article|book|code|idea",
    "title": "string",
    "summary": "string",             # LLM-generated summary
    "embedding": "[float]",          # 1536 dims for semantic search
    "processed_at": "datetime",
    "obsidian_path": "string"        # Path to source-of-truth note in Obsidian
}

CONCEPT_NODE = {
    "id": "uuid",                    # Unique concept identifier
    "name": "string",                # Concept name (e.g., "Attention Mechanism")
    "definition": "string",          # Concise definition
    "domain": "string",              # Knowledge domain (e.g., "machine_learning")
    "complexity": "foundational|intermediate|advanced",
    "embedding": "[float]",          # For semantic similarity queries
    "obsidian_path": "string"        # Optional: if concept has dedicated note
}

TOPIC_NODE = {
    "id": "uuid",                    # Unique topic identifier
    "name": "string",                # Display name (e.g., "Transformers")
    "path": "string",                # Hierarchical path (e.g., "ml/deep-learning/transformers")
    "description": "string"
}

# Relationships connect nodes and encode semantic meaning
RELATIONSHIPS = [
    "(:Source)-[:EXPLAINS {quality: float}]->(:Concept)",    # Source explains a concept
    "(:Source)-[:RELATES_TO {strength: float}]->(:Source)",  # Topical relationship
    "(:Source)-[:CITES]->(:Source)",                         # Citation relationship
    "(:Concept)-[:PREREQUISITE_FOR]->(:Concept)",            # Learning dependency
    "(:Concept)-[:RELATES_TO {type: string}]->(:Concept)",   # Conceptual relationship
    "(:Concept)-[:BELONGS_TO]->(:Topic)",                    # Topic membership
    "(:Source)-[:BELONGS_TO]->(:Topic)",                     # Source categorization
]
```

---

## 5. Database Indexes

Strategic indexes optimize common query patterns. The system prioritizes queries for:
- Due card scheduling (spaced repetition)
- Content processing status monitoring
- Practice analytics aggregation
- Knowledge graph traversal

```sql
-- PostgreSQL indexes for query optimization

-- Content retrieval and processing
CREATE INDEX idx_content_status ON content(processing_status);
CREATE INDEX idx_content_type ON content(source_type);
CREATE INDEX idx_content_hash ON content(raw_file_hash);  -- Deduplication lookups
CREATE INDEX idx_content_obsidian ON content(obsidian_path);  -- Sync operations
CREATE UNIQUE INDEX idx_content_id ON content(id);  -- UUID lookups

-- Spaced repetition scheduling (critical for daily reviews)
CREATE INDEX idx_cards_due ON spaced_rep_cards(due_date) WHERE due_date IS NOT NULL AND NOT suspended;
CREATE INDEX idx_cards_context ON spaced_rep_cards(context_note_id);  -- Find cards from note
CREATE INDEX idx_cards_tags ON spaced_rep_cards USING GIN(tags);  -- Tag-based filtering

-- Practice analytics
CREATE INDEX idx_attempts_session ON practice_attempts(session_id);
CREATE INDEX idx_attempts_concept ON practice_attempts(concept_id);
CREATE INDEX idx_attempts_date ON practice_attempts(created_at);
CREATE INDEX idx_attempts_type ON practice_attempts(exercise_type);

-- Card review history
CREATE INDEX idx_reviews_card ON card_reviews(card_id);
CREATE INDEX idx_reviews_date ON card_reviews(reviewed_at);

-- Mastery trend analysis
CREATE INDEX idx_mastery_topic ON mastery_snapshots(topic_path);
CREATE INDEX idx_mastery_concept ON mastery_snapshots(concept_id);
CREATE INDEX idx_mastery_date ON mastery_snapshots(snapshot_date);

-- Composite indexes for common queries
CREATE INDEX idx_attempts_concept_date ON practice_attempts(concept_id, created_at DESC);
CREATE INDEX idx_mastery_topic_date ON mastery_snapshots(topic_path, snapshot_date DESC);
```

```cypher
// Neo4j indexes for graph queries

// Unique constraints (also create indexes)
CREATE CONSTRAINT source_id IF NOT EXISTS FOR (s:Source) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT topic_id IF NOT EXISTS FOR (t:Topic) REQUIRE t.id IS UNIQUE;

// Additional indexes for common lookups
CREATE INDEX source_type IF NOT EXISTS FOR (s:Source) ON (s.type);
CREATE INDEX source_obsidian IF NOT EXISTS FOR (s:Source) ON (s.obsidian_path);
CREATE INDEX concept_domain IF NOT EXISTS FOR (c:Concept) ON (c.domain);
CREATE INDEX concept_complexity IF NOT EXISTS FOR (c:Concept) ON (c.complexity);
CREATE INDEX topic_path IF NOT EXISTS FOR (t:Topic) ON (t.path);

// Vector index for semantic search (Neo4j 5.x+)
CREATE VECTOR INDEX source_embedding IF NOT EXISTS FOR (s:Source) ON s.embedding
OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX concept_embedding IF NOT EXISTS FOR (c:Concept) ON c.embedding
OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}};
```

---

## 6. Data Synchronization

Since Obsidian is the source of truth, the system implements periodic synchronization to handle manual edits to notes:

1. **Vault Scanner**: Watches for file changes in the Obsidian vault
2. **Reconciliation**: Compares note frontmatter UUIDs with database records
3. **Update Propagation**: Pushes changes from Obsidian to PostgreSQL and Neo4j
4. **Conflict Resolution**: Obsidian always wins; database records are overwritten

```python
# Sync status tracking
class SyncState(BaseModel):
    """Tracks synchronization between Obsidian and databases."""
    last_sync: datetime
    notes_scanned: int
    notes_updated: int
    notes_created: int
    conflicts_resolved: int
    errors: list[str]
```

---

## 7. Related Documents

- `04_knowledge_graph_neo4j.md` — Full Neo4j schema and query patterns
- `05_learning_system.md` — Practice generation and spaced rep logic
- `06_backend_api.md` — API endpoints using these models
- `07_obsidian_integration.md` — Obsidian vault structure and sync details
