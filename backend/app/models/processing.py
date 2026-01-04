"""
LLM Processing Data Models (Pydantic)

Pydantic models for the LLM processing pipeline. These models ensure type safety
and validation throughout processing stages. Each stage produces structured output
that downstream stages and output generators can rely on.

ARCHITECTURE NOTE:
    This file contains PYDANTIC models for data validation and pipeline flow.
    There is a corresponding SQLAlchemy file: app/db/models_processing.py

    Why two files?
    - Pydantic models: JSON parsing, API validation, pipeline data flow
    - SQLAlchemy models: Database schema, ORM, persistence, foreign keys

    Data flows: LLM Output → Pydantic → Pipeline → SQLAlchemy → Database

    Fields like `processing_run_id` and `content_id` (foreign keys) exist only
    in SQLAlchemy since they're database concerns, not pipeline concerns.

Models:
- ContentAnalysis: Result of initial content analysis
- Concept: Extracted concept with definition and context
- ExtractionResult: All extracted entities (concepts, findings, tools, etc.)
- TagAssignment: Assigned tags from controlled vocabulary
- Connection: Relationship to existing knowledge
- FollowupTask: Generated actionable task
- MasteryQuestion: Generated mastery question for learning
- ProcessingResult: Complete pipeline result

Usage:
    from app.enums import ConceptImportance
    from app.models.processing import ProcessingResult, ContentAnalysis, Concept

    result = ProcessingResult(
        content_id="...",
        analysis=ContentAnalysis(content_type="PAPER", domain="ml", ...),
        ...
    )
"""

from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, Field

from app.enums.processing import ConceptImportance


class ContentAnalysis(BaseModel):
    """
    Result of initial content analysis.

    This is the first processing stage output that determines how subsequent
    stages behave. Identifying content type, domain, complexity, and key topics
    allows the pipeline to use appropriate prompts and model configurations.

    Attributes:
        content_type: Type of content (paper, article, book, code, idea, voice_memo)
        domain: Primary domain (ml, systems, leadership, productivity, etc.)
        complexity: Difficulty level (foundational, intermediate, advanced)
        estimated_length: Content length category (short, medium, long)
        has_code: Whether content contains code snippets
        has_math: Whether content contains mathematical notation
        has_diagrams: Whether content contains diagrams or figures
        key_topics: Main topics covered (up to 10)
        language: ISO language code (default: en)
    """

    content_type: str = Field(
        ..., description="Type: paper, article, book, code, idea, voice_memo"
    )
    domain: str = Field(
        ..., description="Primary domain: ml, systems, leadership, productivity, etc."
    )
    complexity: str = Field(
        ..., description="Difficulty: foundational, intermediate, advanced"
    )
    estimated_length: str = Field(
        ..., description="Length category: short, medium, long"
    )
    has_code: bool = Field(default=False)
    has_math: bool = Field(default=False)
    has_diagrams: bool = Field(default=False)
    key_topics: list[str] = Field(
        default_factory=list, description="Main topics covered (up to 10)"
    )
    language: str = Field(default="en", description="ISO language code")


class Concept(BaseModel):
    """
    Extracted concept with context.

    Concepts are the atomic units of knowledge in the graph. They enable
    rich querying, connection discovery, and knowledge gap identification.

    Attributes:
        id: Unique identifier (UUID v4)
        name: Concept name (e.g., "attention mechanism", "transformer")
        definition: Clear, concise definition in 1-2 sentences
        context: How this concept is used in THIS specific content
        importance: Role in the content (core, supporting, tangential)
        related_concepts: Other concepts this one connects to
        embedding: Vector embedding for similarity search (computed post-extraction)
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Concept name")
    definition: str = Field(..., description="Clear definition in 1-2 sentences")
    context: str = Field(
        default="", description="How it's used in this specific content"
    )
    importance: str = Field(
        default=ConceptImportance.SUPPORTING.value,
        description="CORE, SUPPORTING, or TANGENTIAL",
    )
    related_concepts: list[str] = Field(
        default_factory=list, description="Names of related concepts in this content"
    )
    embedding: Optional[list[float]] = Field(
        default=None,
        description="Vector embedding for similarity search (computed post-extraction)",
    )
    neo4j_node_id: Optional[str] = Field(
        default=None, description="ID of corresponding Neo4j node (set after storage)"
    )


class ExtractionResult(BaseModel):
    """
    Result of concept extraction stage.

    Contains all structured information extracted from content including
    concepts, key findings, methodologies, tools, and people mentioned.

    Attributes:
        concepts: List of extracted concepts with definitions
        key_findings: Main insights, conclusions, or claims
        methodologies: Approaches, techniques, algorithms described
        tools_mentioned: Software, frameworks, libraries mentioned
        people_mentioned: Authors, researchers, thought leaders referenced
    """

    concepts: list[Concept] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)
    methodologies: list[str] = Field(default_factory=list)
    tools_mentioned: list[str] = Field(default_factory=list)
    people_mentioned: list[str] = Field(default_factory=list)


class TagAssignment(BaseModel):
    """
    Result of tag classification stage.

    Tags are assigned from a controlled vocabulary (tag taxonomy) to ensure
    consistency across the knowledge base. Tags enable filtering, grouping,
    and discovering content by domain, status, or quality level.

    Attributes:
        domain_tags: Tags from the domain taxonomy (e.g., ml/transformers/attention)
        meta_tags: Status and quality tags (e.g., status/actionable, quality/deep-dive)
        suggested_new_tags: Tags suggested if taxonomy has gaps
        reasoning: Brief explanation of tag choices
    """

    domain_tags: list[str] = Field(default_factory=list)
    meta_tags: list[str] = Field(default_factory=list)
    suggested_new_tags: list[str] = Field(default_factory=list)
    reasoning: str = Field(default="")


class Connection(BaseModel):
    """
    Connection to existing knowledge.

    Represents a semantic relationship between new content and existing
    content in the knowledge graph. Enables the "web" of connections.

    Attributes:
        id: Unique identifier for this connection
        target_id: ID of the connected content/concept
        target_title: Title of the connected item (for display)
        relationship_type: Type of relationship (RELATES_TO, EXTENDS, etc.)
        strength: Connection strength from 0.0 to 1.0
        explanation: Brief explanation of why these are connected
        verified_by_user: Whether user has confirmed this connection
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    target_id: str = Field(..., description="ID of connected content/concept")
    target_title: str = Field(..., description="Title for display")
    relationship_type: str = Field(
        default="RELATES_TO",
        description="RELATES_TO, EXTENDS, CONTRADICTS, PREREQUISITE_FOR, APPLIES",
    )
    strength: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Connection strength (0-1)"
    )
    explanation: str = Field(default="", description="Why these are connected")
    verified_by_user: bool = Field(
        default=False, description="Whether user has confirmed this connection"
    )


class FollowupTask(BaseModel):
    """
    Generated follow-up task.

    Follow-up tasks transform passive reading into active learning. They help
    users engage more deeply with content by providing specific, actionable
    next steps.

    Attributes:
        id: Unique identifier
        task: Specific, actionable task description
        task_type: Category (research, practice, connect, apply, review)
        priority: Importance level (high, medium, low)
        estimated_time: Time estimate (15min, 30min, 1hr, 2hr+)
        completed: Whether the task has been completed
        completed_at: When the task was completed
        created_at: When the task was created
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task: str = Field(..., description="Specific, actionable task description")
    task_type: str = Field(
        default="research", description="research, practice, connect, apply, review"
    )
    priority: str = Field(default="medium", description="high, medium, low")
    estimated_time: str = Field(default="30min", description="15min, 30min, 1hr, 2hr+")
    completed: bool = Field(default=False, description="Whether task is done")
    completed_at: Optional[datetime] = Field(
        default=None, description="When the task was completed"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="When the task was created"
    )


class MasteryQuestion(BaseModel):
    """
    Generated mastery question.

    Mastery questions enable active recall and self-testing. If a user can
    answer these questions from memory, they truly understand the material.

    Attributes:
        id: Unique identifier
        question: Clear, specific question text
        question_type: Category (conceptual, application, analysis, synthesis)
        difficulty: Level (foundational, intermediate, advanced)
        hints: Progressive hints for struggling users
        key_points: Key points a good answer should include
        next_review_at: When to show again (spaced repetition)
        review_count: Number of times reviewed
        ease_factor: SM-2 ease factor for spaced repetition
        created_at: When the question was created
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str = Field(..., description="Clear, specific question")
    question_type: str = Field(
        default="conceptual", description="conceptual, application, analysis, synthesis"
    )
    difficulty: str = Field(
        default="intermediate", description="foundational, intermediate, advanced"
    )
    hints: list[str] = Field(default_factory=list, description="Progressive hints")
    key_points: list[str] = Field(
        default_factory=list, description="Key points for a good answer"
    )
    # Spaced repetition state
    next_review_at: Optional[datetime] = Field(
        default=None, description="When to show again (spaced repetition)"
    )
    review_count: int = Field(default=0, description="Number of times reviewed")
    ease_factor: float = Field(
        default=2.5, description="SM-2 ease factor for spaced repetition"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="When the question was created"
    )


class ProcessingResult(BaseModel):
    """
    Complete result of the processing pipeline.

    Aggregates results from all processing stages along with metadata about
    processing time and cost. This is the final output that gets persisted
    and used for output generation.

    Attributes:
        content_id: ID of the processed content
        analysis: Content analysis result
        summaries: Dict mapping level (brief/standard/detailed) to summary text
        extraction: Extracted concepts and entities
        tags: Assigned tags
        connections: Discovered connections to existing knowledge
        followups: Generated follow-up tasks
        mastery_questions: Generated mastery questions
        obsidian_note_path: Path to generated Obsidian note (if created)
        neo4j_node_id: ID of created Neo4j node (if created)
        processing_time_seconds: Total pipeline execution time
        estimated_cost_usd: Estimated total LLM cost
        processed_at: Timestamp when processing completed
    """

    content_id: str = Field(..., description="ID of processed content")
    analysis: ContentAnalysis
    summaries: dict[str, str] = Field(
        default_factory=dict, description="level -> summary text"
    )
    extraction: ExtractionResult = Field(default_factory=ExtractionResult)
    tags: TagAssignment = Field(default_factory=TagAssignment)
    connections: list[Connection] = Field(default_factory=list)
    followups: list[FollowupTask] = Field(default_factory=list)
    mastery_questions: list[MasteryQuestion] = Field(default_factory=list)

    # Output paths
    obsidian_note_path: Optional[str] = None
    neo4j_node_id: Optional[str] = None

    # Metrics
    processing_time_seconds: float = Field(default=0.0)
    estimated_cost_usd: float = Field(default=0.0)
    processed_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "content_id": "123e4567-e89b-12d3-a456-426614174000",
                "analysis": {
                    "content_type": "paper",
                    "domain": "ml",
                    "complexity": "advanced",
                    "estimated_length": "long",
                    "has_code": True,
                    "has_math": True,
                    "has_diagrams": True,
                    "key_topics": ["transformers", "attention", "self-attention"],
                    "language": "en",
                },
                "summaries": {
                    "brief": "Introduces the Transformer architecture...",
                    "standard": "This paper presents a new neural network...",
                    "detailed": "## Overview\n\nThe Transformer architecture...",
                },
                "processing_time_seconds": 45.2,
                "estimated_cost_usd": 0.15,
            }
        }
