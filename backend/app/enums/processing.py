"""
Processing-related enums.

Defines enums for LLM processing stages, run statuses, content analysis, and summary levels.
"""

from enum import Enum


class ProcessingStage(str, Enum):
    """Processing pipeline stages that can be selectively run."""

    ANALYSIS = "ANALYSIS"
    SUMMARIZATION = "SUMMARIZATION"
    EXTRACTION = "EXTRACTION"
    TAGGING = "TAGGING"
    CONNECTIONS = "CONNECTIONS"
    FOLLOWUPS = "FOLLOWUPS"
    QUESTIONS = "QUESTIONS"


class ProcessingRunStatus(str, Enum):
    """Status of a processing run."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SummaryLevel(str, Enum):
    """Summary detail levels for multi-level summarization."""

    BRIEF = "BRIEF"  # 1-2 sentences
    STANDARD = "STANDARD"  # 1-2 paragraphs
    DETAILED = "DETAILED"  # Full summary with sections


class ContentDomain(str, Enum):
    """Primary domain/field of content."""

    # Technical domains
    ML = "ML"  # Machine learning, AI, deep learning
    SYSTEMS = "SYSTEMS"  # Distributed systems, infrastructure
    SOFTWARE = "SOFTWARE"  # Software engineering, programming
    DATA = "DATA"  # Data engineering, analytics
    SECURITY = "SECURITY"  # Cybersecurity, cryptography

    # Business/Professional
    LEADERSHIP = "LEADERSHIP"  # Management, leadership, teams
    PRODUCTIVITY = "PRODUCTIVITY"  # Personal productivity, workflows
    BUSINESS = "BUSINESS"  # Strategy, entrepreneurship
    CAREER = "CAREER"  # Career development, job search

    # Academic/Research
    SCIENCE = "SCIENCE"  # Natural sciences, research
    MATH = "MATH"  # Mathematics, statistics

    # Other
    GENERAL = "GENERAL"  # General interest, misc


class ContentComplexity(str, Enum):
    """Complexity/difficulty level of content."""

    FOUNDATIONAL = "FOUNDATIONAL"  # Introductory, explains basics
    INTERMEDIATE = "INTERMEDIATE"  # Assumes some background knowledge
    ADVANCED = "ADVANCED"  # Requires deep domain expertise


class ContentLength(str, Enum):
    """Estimated length category of content."""

    SHORT = "SHORT"  # < 2000 words
    MEDIUM = "MEDIUM"  # 2000-10000 words
    LONG = "LONG"  # > 10000 words


class ConceptImportance(str, Enum):
    """Importance level of an extracted concept."""

    CORE = "CORE"  # Central to understanding the content
    SUPPORTING = "SUPPORTING"  # Helps understand core concepts
    TANGENTIAL = "TANGENTIAL"  # Mentioned but not essential


class FollowupTaskType(str, Enum):
    """Types of follow-up tasks for active learning."""

    RESEARCH = "RESEARCH"  # Look up X to understand Y better
    PRACTICE = "PRACTICE"  # Try implementing X
    CONNECT = "CONNECT"  # Explore how this relates to Z
    APPLY = "APPLY"  # Use this technique on project W
    REVIEW = "REVIEW"  # Revisit X after applying this


class FollowupPriority(str, Enum):
    """Priority levels for follow-up tasks."""

    HIGH = "HIGH"  # Fundamental to understanding, should do soon
    MEDIUM = "MEDIUM"  # Would deepen understanding
    LOW = "LOW"  # Nice to have, optional enrichment


class FollowupTimeEstimate(str, Enum):
    """Estimated time to complete a follow-up task."""

    FIFTEEN_MIN = "15MIN"
    THIRTY_MIN = "30MIN"
    ONE_HOUR = "1HR"
    TWO_HOURS_PLUS = "2HR_PLUS"


class QuestionType(str, Enum):
    """Types of mastery questions for testing understanding."""

    CONCEPTUAL = "conceptual"  # "What is X and why does it matter?"
    APPLICATION = "application"  # "How would you use X to solve Y?"
    ANALYSIS = "analysis"  # "Why does X lead to Y?"
    SYNTHESIS = "synthesis"  # "How does X connect to Z?"


class QuestionDifficulty(str, Enum):
    """Difficulty levels for mastery questions."""

    FOUNDATIONAL = "foundational"  # "what" and "how" questions, basic understanding
    INTERMEDIATE = "intermediate"  # "why" and "when to use" questions
    ADVANCED = "advanced"  # edge cases, trade-offs, design questions


class RelationshipType(str, Enum):
    """
    Relationship types for the knowledge graph.

    Content -> Concept:
    - CONTAINS: Content contains a concept

    Content -> Content:
    - RELATES_TO: General topical relationship, shared themes or concepts
    - EXTENDS: Builds on, continues, or deepens existing content
    - CONTRADICTS: Challenges, refutes, or disagrees with existing content
    - PREREQUISITE_FOR: Foundational for understanding
    - APPLIES: Applies concepts, methods, or ideas from another

    Content -> Tag:
    - HAS_TAG: Content has a tag

    Concept -> Concept:
    - RELATED_TO: Concepts are related
    """

    # Content -> Concept
    CONTAINS = "CONTAINS"

    # Content -> Content
    RELATES_TO = "RELATES_TO"
    EXTENDS = "EXTENDS"
    CONTRADICTS = "CONTRADICTS"
    PREREQUISITE_FOR = "PREREQUISITE_FOR"
    APPLIES = "APPLIES"

    # Content -> Tag
    HAS_TAG = "HAS_TAG"

    # Concept -> Concept
    RELATED_TO = "RELATED_TO"


class TagCategory(str, Enum):
    """Categories of tags in the taxonomy."""

    DOMAIN = "DOMAIN"  # Topic/field tags (e.g., ml/transformers)
    STATUS = "STATUS"  # Processing status tags (e.g., to-review, archived)
    QUALITY = "QUALITY"  # Quality level tags (e.g., high-value, needs-work)


class NodeType(str, Enum):
    """Node types in the Neo4j knowledge graph."""

    CONTENT = "Content"  # Papers, articles, books, code, ideas, voice memos
    CONCEPT = "Concept"  # Key concepts, terms, ideas extracted from content
    TAG = "Tag"  # Tags from the controlled taxonomy
